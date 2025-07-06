#!/usr/bin/env bash
#
# Configure the Robot Hat I²S audio overlay, ALSA, and PulseAudio settings.
# Detect Robot Hat via I²C, install and load correct overlay, then configure audio.

# Global variables
VERSION="0.0.4"
USERNAME=${SUDO_USER:-$LOGNAME}
USER_RUN="sudo -u ${USERNAME} env XDG_RUNTIME_DIR=/run/user/$(id -u ${USERNAME})"

# Determine boot and overlays directories
if [ -d /boot/firmware ]; then
  BOOTDIR=/boot/firmware
else
  BOOTDIR=/boot
fi
CONFIG="$BOOTDIR/config.txt"
OVERLAYS_DIR="$BOOTDIR/overlays"
ASOUND_CONF="/etc/asound.conf"

# Overlays and card names
DTOVERLAY_WITHOUT_MIC="hifiberry-dac"
AUDIO_CARD_NAME_WITHOUT_MIC="sndrpihifiberry"

DTOVERLAY_WITH_MIC="googlevoicehat-soundcard"
AUDIO_CARD_NAME_WITH_MIC="sndrpigooglevoicehat"

SOFTVOL_SPEAKER_NAME="robot-hat speaker"
SOFTVOL_MIC_NAME="robot-hat mic"

# Helper functions for logging
debug(){ echo -e "[DEBUG] $*"; }
success(){ echo -e "[OK] $*"; }
info(){ echo -e "[INFO] $*"; }
warning(){ echo -e "[WARN] $*"; }
error(){ echo -e "[ERROR] $*"; }

# Must run as root
sudocheck(){
  if [ "$(id -u)" -ne 0 ]; then
    error "Run as root: sudo bash ./i2samp.sh"
    exit 1
  fi
}

# Check for sound card index
get_card_index(){
  grep "$1" <(aplay -l) | awk '/card/ {print $2}' | tr -d ':' | head -n1
}

# Generate ALSA config for no-mic
config_asound_without_mic(){
  cp "$ASOUND_CONF" "${ASOUND_CONF}.old" 2>/dev/null || :
  cat > "$ASOUND_CONF" <<EOF
pcm.speaker { type hw; card $AUDIO_CARD_NAME_WITHOUT_MIC }
pcm.dmixer { type dmix; ipc_key 1024; ipc_perm 0666; slave { pcm "speaker"; rate 44100; channels 2 } }
ctl.dmixer { type hw; card $AUDIO_CARD_NAME_WITHOUT_MIC }
pcm.softvol { type softvol; slave.pcm "dmixer"; control { name "$SOFTVOL_SPEAKER_NAME Playback Volume"; card $AUDIO_CARD_NAME_WITHOUT_MIC } }
pcm.robothat { type plug; slave.pcm "softvol" }
ctl.robothat { type hw; card $AUDIO_CARD_NAME_WITHOUT_MIC }
pcm.!default robothat
EOF
}

# Generate ALSA config for with-mic
config_asound_with_mic(){
  cp "$ASOUND_CONF" "${ASOUND_CONF}.old" 2>/dev/null || :
  cat > "$ASOUND_CONF" <<EOF
pcm.robothat { type asym; playback.pcm { type plug; slave.pcm "speaker" }; capture.pcm { type plug; slave.pcm "mic" } }
pcm.speaker_hw { type hw; card $AUDIO_CARD_NAME_WITH_MIC; device 0 }
pcm.dmixer { type dmix; ipc_key 1024; ipc_perm 0666; slave { pcm "speaker_hw"; rate 44100; channels 2 } }
ctl.dmixer { type hw; card $AUDIO_CARD_NAME_WITH_MIC }
pcm.speaker { type softvol; slave.pcm "dmixer"; control { name "$SOFTVOL_SPEAKER_NAME Playback Volume"; card $AUDIO_CARD_NAME_WITH_MIC } }
pcm.mic_hw { type hw; card $AUDIO_CARD_NAME_WITH_MIC; device 0 }
pcm.mic { type softvol; slave.pcm "mic_hw"; control { name "$SOFTVOL_MIC_NAME Capture Volume"; card $AUDIO_CARD_NAME_WITH_MIC } }
ctl.robothat { type hw; card $AUDIO_CARD_NAME_WITH_MIC }
pcm.!default robothat
EOF
}

# Main installation routine
main(){
  sudocheck

  # Detect Robot Hat presence via I2C addresses 0x14 or 0x15
  if i2cdetect -y 1 | grep -qwE '(^|[[:space:]])(14|15)([[:space:]]|$)'; then
    _is_with_mic=true
    dtoverlay_name="$DTOVERLAY_WITH_MIC"
    audio_card_name="$AUDIO_CARD_NAME_WITH_MIC"
    info "Robot Hat detected via I2C: using mic overlay"
  else
    _is_with_mic=false
    dtoverlay_name="$DTOVERLAY_WITHOUT_MIC"
    audio_card_name="$AUDIO_CARD_NAME_WITHOUT_MIC"
    warning "No Robot Hat detected via I2C: using no-mic overlay"
  fi

  # Ensure overlay .dtbo exists in overlays directory
  if [ ! -f "$OVERLAYS_DIR/${dtoverlay_name}.dtbo" ]; then
    if [ -d "$(dirname "$0")/dtoverlays" ] && [ -f "$(dirname "$0")/dtoverlays/${dtoverlay_name}.dtbo" ]; then
      info "Copying ${dtoverlay_name}.dtbo to $OVERLAYS_DIR"
      cp "$(dirname "$0")/dtoverlays/${dtoverlay_name}.dtbo" "$OVERLAYS_DIR/"
    else
      error "Overlay ${dtoverlay_name}.dtbo not found in $OVERLAYS_DIR or repo dtoverlays"
      exit 1
    fi
  fi

  # Persist overlay into config.txt
  info "Installing overlay: $dtoverlay_name into $CONFIG"
  sed -i "/^dtoverlay=${DTOVERLAY_WITH_MIC}/d" "$CONFIG"
  sed -i "/^dtoverlay=${DTOVERLAY_WITHOUT_MIC}/d" "$CONFIG"
  echo "dtoverlay=$dtoverlay_name" | tee -a "$CONFIG"

  # Dynamically load overlay
  info "Loading overlay: $dtoverlay_name..."
  dtoverlay "$dtoverlay_name" || { error "Failed to load overlay $dtoverlay_name"; exit 1; }
  sleep 1

  # Verify card appears
  idx=$(get_card_index "$audio_card_name")
  if [ -z "$idx" ]; then
    error "Soundcard $audio_card_name not found after loading overlay"
    echo "Run: speaker-test -l1 -c2" >&2
    exit 1
  fi

  # Configure ALSA
  info "Configuring ALSA for $audio_card_name..."
  if [ "$_is_with_mic" = true ]; then
    config_asound_with_mic
  else
    config_asound_without_mic
  fi
  systemctl restart alsa-utils

  # Set volumes
  info "Setting speaker volume to 100%"
  amixer -c "$audio_card_name" sset "$SOFTVOL_SPEAKER_NAME" 100% || :
  if [ "$_is_with_mic" = true ]; then
    info "Setting mic volume to 100%"
    amixer -c "$audio_card_name" sset "$SOFTVOL_MIC_NAME" 100% || :
  fi

  # Start PulseAudio and set default sink
  info "Starting PulseAudio..."
  raspi-config nonint do_audioconf 1 2>/dev/null || :
  $USER_RUN pulseaudio -D 2>/dev/null || :
  sink=$(get_card_index "$audio_card_name")
  $USER_RUN pactl set-default-sink "$sink" 2>/dev/null || :

  success "Audio configuration complete"
}

main
exit 0
