#!/usr/bin/env bash
#
# Configure the Robot Hat I²S audio overlay, ALSA, and PulseAudio settings.
#

VERSION="0.0.4"
USERNAME=${SUDO_USER:-$LOGNAME}
USER_RUN="sudo -u ${USERNAME} env XDG_RUNTIME_DIR=/run/user/$(id -u ${USERNAME})"

CONFIG="/boot/firmware/config.txt"
if ! test -f "$CONFIG"; then
    CONFIG="/boot/config.txt"
fi

ASOUND_CONF="/etc/asound.conf"

DTOVERLAY_NO_MIC="hifiberry-dac"
CARD_NAME_NO_MIC="sndrpihifiberry"

DTOVERLAY_MIC="googlevoicehat-soundcard"
CARD_NAME_MIC="sndrpigooglevoi"

SOFTVOL_SPEAKER_NAME="robot-hat speaker"
SOFTVOL_MIC_NAME="robot-hat mic"

HAT_UUIDS=("9daeea78-0000-076e-0032-582369ac3e02")
HAT_DEVICE_TREE="/proc/device-tree/"

_is_with_mic=false
overlay=""
card=""

success(){ echo -e "\e[32m$1\e[0m"; }
info  (){ echo -e "\e[36m$1\e[0m"; }
warning(){ echo -e "\e[33m$1\e[0m"; }
error (){ echo -e "\e[31m$1\e[0m"; }

sudocheck(){
  if [ "$(id -u)" -ne 0 ]; then
    error "Must be root. Use sudo $0"
    exit 1
  fi
}

detect_hat(){
  for d in ${HAT_DEVICE_TREE}*hat*; do
    [ ! -d "$d" ] && continue
    if [ -f "$d/uuid" ]; then
      u=$(tr -d '\0' <"$d/uuid")
      for hu in "${HAT_UUIDS[@]}"; do
        if [ "$u" = "$hu" ]; then
          info "Robot Hat detected via I2C: UUID $u"
          _is_with_mic=true
          return
        fi
      done
    fi
  done
  warning "No Robot Hat detected; defaulting to no-mic overlay"
  _is_with_mic=false
}

get_card_index(){
  local name=$1
  idx=$(aplay -l | grep "$name" | awk '/card/ {print $2}' | tr -d ':' | head -n1)
  echo $idx
}

config_asound_no_mic(){
  cat >"$ASOUND_CONF" <<EOF
pcm.speaker {
  type hw
  card $card
}
pcm.dmixer {
  type dmix
  ipc_key 1024
  ipc_perm 0666
  slave {
    pcm "speaker"
    period_time 0
    period_size 1024
    buffer_size 8192
    rate 44100
    channels 2
  }
}
ctl.dmixer { type hw; card $card; }
pcm.softvol {
  type softvol
  slave.pcm "dmixer"
  control.name "$SOFTVOL_SPEAKER_NAME Playback Volume"
  control.card $card
  min_dB -51.0
  max_dB 0.0
}
pcm.!default softvol
ctl.!default softvol
EOF
  success "Written $ASOUND_CONF for HiFiBerry DAC"
}

config_asound_mic(){
  cat >"$ASOUND_CONF" <<EOF
pcm.robothat {
  type asym
  playback.pcm { type plug; slave.pcm "speaker"; }
  capture.pcm  { type plug; slave.pcm "mic"; }
}
pcm.speaker {
  type hw
  card $card
  device 0
}
pcm.dmixer { 
  type dmix; ipc_key 1024; ipc_perm 0666;
  slave { pcm "speaker"; rate 44100; channels 2; }
}
ctl.dmixer { type hw; card $card; }
pcm.softvol {
  type softvol
  slave.pcm "dmixer"
  control.name "$SOFTVOL_SPEAKER_NAME Playback Volume"
  control.card $card
  min_dB -51.0; max_dB 0.0
}
pcm.mic {
  type hw
  card $card
  device 0
}
ctl.mic { type hw; card $card; }
pcm.!default robothat
ctl.!default robothat
EOF
  success "Written $ASOUND_CONF for Voice HAT"
}

main(){
  sudocheck
  detect_hat

  if [ "$_is_with_mic" = true ]; then
    info "Using mic overlay → $DTOVERLAY_MIC"
    overlay=$DTOVERLAY_MIC
    card=$CARD_NAME_MIC
  else
    info "Forcing no-mic overlay → $DTOVERLAY_NO_MIC"
    overlay=$DTOVERLAY_NO_MIC
    card=$CARD_NAME_NO_MIC
  fi

  # add dtoverlay to config.txt if missing
  if ! grep -q "^dtoverlay=${overlay}" "$CONFIG"; then
    echo "" >>"$CONFIG"
    echo "dtoverlay=${overlay}" >>"$CONFIG"
    success "Added dtoverlay=${overlay} to $CONFIG"
  else
    info "dtoverlay=${overlay} already in $CONFIG"
  fi

  info "Loading overlay: $overlay"
  dtoverlay "$overlay" || warning "Failed to load dtoverlay $overlay (kernel may not support)"

  sleep 1
  idx=$(get_card_index "$card")
  if [ -z "$idx" ]; then
    error "Soundcard $card not found; you may need to reboot"
    exit 1
  fi
  success "Detected $card as card $idx"

  if [ "$_is_with_mic" = true ]; then
    config_asound_mic
  else
    config_asound_no_mic
  fi

  info "Setting ALSA volume to 100%"
  amixer -c "$idx" sset 'PCM' 100% >/dev/null 2>&1 || warning "Failed to set PCM volume"

  info "Enabling PulseAudio"
  raspi-config nonint do_audioconf 1 >/dev/null 2>&1
  $USER_RUN pulseaudio -D >/dev/null 2>&1 || warning "Could not start PulseAudio"

  info "Setting default Pulse sink to card $idx"
  $USER_RUN pactl set-default-sink "$idx" >/dev/null 2>&1 || warning "Failed to set default sink"

  success "I²S audio configuration complete!"
}

main
exit 0