#!/usr/bin/env bash
#
# Configure the Robot Hat I²S audio overlay, ALSA, and PulseAudio settings.
#

# global variables
VERSION="0.0.4"
USERNAME=${SUDO_USER:-$LOGNAME}
USER_RUN="sudo -u ${USERNAME} env XDG_RUNTIME_DIR=/run/user/$(id -u ${USERNAME})"

CONFIG="/boot/firmware/config.txt"
# Fall back to the old config.txt path
if ! test -f "$CONFIG"; then
    CONFIG="/boot/config.txt"
fi

ASOUND_CONF="/etc/asound.conf"

# ----- robot hat without onboard mic -----
DTOVERLAY_WITHOUT_MIC="hifiberry-dac"
AUDIO_CARD_NAME_WITHOUT_MIC="sndrpihifiberry"
ALSA_CARD_NAME_WITHOUT_MIC="snd_rpi_hifiberry_dac"

# ----- robot hat with onboard mic -----
DTOVERLAY_WITH_MIC="googlevoicehat-soundcard"
AUDIO_CARD_NAME_WITH_MIC="sndrpigooglevoi"
ALSA_CARD_NAME_WITH_MIC="snd_rpi_googlevoicehat_soundcar"

SOFTVOL_SPEAKER_NAME="robot-hat speaker"
SOFTVOL_MIC_NAME="robot-hat mic"

# ----- robot hat 5 detection -----
HAT_DEVICE_TREE="/proc/device-tree/"
HAT_UUIDs=(
    "9daeea78-0000-076e-0032-582369ac3e02"
)
ROBOTHAT5_PRODUCT_VER=50
robothat_spk_en=20
_is_with_mic=true
dtoverlay_name=""
audio_card_name=""
alsa_card_name=""

# ------------------------------------------------------------------------------
success() { echo -e "$(tput setaf 2)$1$(tput sgr0)"; }
info()    { echo -e "$(tput setaf 6)$1$(tput sgr0)"; }
warning() { echo -e "$(tput setaf 3)$1$(tput sgr0)"; }
error()   { echo -e "$(tput setaf 1)$1$(tput sgr0)"; }
newline() { echo ""; }

sudocheck() {
    if [ "$(id -u)" -ne 0 ]; then
        error "Must be root. Use sudo ./i2samp.sh"
        exit 1
    fi
}

ask_reboot() {
    read -r -p "$1 [y/N] " response </dev/tty
    if [[ $response =~ ^[Yy]$ ]]; then
        info "Rebooting now..."
        sync && reboot
    fi
}

get_soundcard_index() {
    grep "$1" <(aplay -l) | awk '/card/ {print $2}' | tr -d ':' | head -n1
}

config_asound_without_mic() {
    [ -f "$ASOUND_CONF" ] && cp "$ASOUND_CONF" "${ASOUND_CONF}.old"
    cat > "$ASOUND_CONF" <<EOF
pcm.speaker {
    type hw
    card $AUDIO_CARD_NAME_WITHOUT_MIC
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
ctl.dmixer {
    type hw
    card $AUDIO_CARD_NAME_WITHOUT_MIC
}
pcm.softvol {
    type softvol
    slave.pcm "dmixer"
    control {
        name "$SOFTVOL_SPEAKER_NAME Playback Volume"
        card $AUDIO_CARD_NAME_WITHOUT_MIC
    }
    min_dB -51.0
    max_dB 0.0
}
pcm.robothat {
    type plug
    slave.pcm "softvol"
}
ctl.robothat {
    type hw
    card $AUDIO_CARD_NAME_WITHOUT_MIC
}
pcm.!default robothat
ctl.!default robothat
EOF
}

config_asound_with_mic() {
    [ -f "$ASOUND_CONF" ] && cp "$ASOUND_CONF" "${ASOUND_CONF}.old"
    cat > "$ASOUND_CONF" <<EOF
pcm.robothat {
    type asym
    playback.pcm {
        type plug
        slave.pcm "speaker"
    }
    capture.pcm {
        type plug
        slave.pcm "mic"
    }
}
pcm.speaker_hw {
    type hw
    card $AUDIO_CARD_NAME_WITH_MIC
    device 0
}
pcm.dmixer {
    type dmix
    ipc_key 1024
    ipc_perm 0666
    slave {
        pcm "speaker_hw"
        period_time 0
        period_size 1024
        buffer_size 8192
        rate 44100
        channels 2
    }
}
ctl.dmixer {
    type hw
    card $AUDIO_CARD_NAME_WITH_MIC
}
pcm.speaker {
    type softvol
    slave.pcm "dmixer"
    control {
        name "$SOFTVOL_SPEAKER_NAME Playback Volume"
        card $AUDIO_CARD_NAME_WITH_MIC
    }
    min_dB -51.0
    max_dB 0.0
}
pcm.mic_hw {
    type hw
    card $AUDIO_CARD_NAME_WITH_MIC
    device 0
}
pcm.mic {
    type softvol
    slave.pcm "mic_hw"
    control {
        name "$SOFTVOL_MIC_NAME Capture Volume"
        card $AUDIO_CARD_NAME_WITH_MIC
    }
    min_dB -26.0
    max_dB 25.0
}
ctl.robothat {
    type hw
    card $AUDIO_CARD_NAME_WITH_MIC
}
pcm.!default robothat
ctl.!default robothat
EOF
}

check_robothat() {
    for dir in /proc/device-tree/*hat*; do
        [ ! -d "$dir" ] && continue
        uuid=$(tr -d '\0' < "$dir"/uuid 2>/dev/null)
        [[ " ${HAT_UUIDs[*]} " == *" $uuid "* ]] && {
            robothat_product_ver=$(printf "%d" 0x$(xxd -p -c4 "$dir"/product_ver))
            _is_with_mic=$([[ $robothat_product_ver -ge $ROBOTHAT5_PRODUCT_VER ]] && echo true || echo false)
            return
        }
    done
    warning "No Robot Hat detected in /proc/device-tree"
}

install_soundcard_driver() {
    sudocheck
    check_robothat

    dtoverlay_name=$(_is_with_mic && echo $DTOVERLAY_WITH_MIC || echo $DTOVERLAY_WITHOUT_MIC)
    audio_card_name=$(_is_with_mic && echo $AUDIO_CARD_NAME_WITH_MIC || echo $AUDIO_CARD_NAME_WITHOUT_MIC)

    info "Applying DTO overlay: $dtoverlay_name"
    dtoverlay "$dtoverlay_name"
    sleep 1

    card_idx=$(get_soundcard_index "$audio_card_name")
    if [ -z "$card_idx" ]; then
        error "Soundcard not found; you may need to reboot."
        ask_reboot "Reboot now?"
        exit 1
    fi

    info "Configuring ALSA (/etc/asound.conf)..."
    if $_is_with_mic; then
        config_asound_with_mic
    else
        config_asound_without_mic
    fi
    systemctl restart alsa-utils 2>/dev/null

    info "Setting volume to 100%..."
    amixer -c "$audio_card_name" sset "$SOFTVOL_SPEAKER_NAME" 100%
    $_is_with_mic && amixer -c "$audio_card_name" sset "$SOFTVOL_MIC_NAME" 100%

    info "Enabling PulseAudio..."
    raspi-config nonint do_audioconf 1 2>/dev/null
    $USER_RUN pulseaudio -D 2>/dev/null

    info "Setting PulseAudio default sink..."
    sink=$(get_soundcard_index "$audio_card_name")
    $USER_RUN pactl set-default-sink "$sink"

    newline
    success "I²S audio configuration complete!"
}

# Execute
install_soundcard_driver
exit 0