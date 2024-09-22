#!/bin/bash

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Function to install WireGuard on Linux
install_wireguard_linux() {
  echo "Installing WireGuard on Linux..."

  # Update package lists
  sudo apt-get update

  # Install WireGuard
  sudo apt-get install -y wireguard
}

# Function to install WireGuard on macOS
install_wireguard_mac() {
  echo "Installing WireGuard on macOS..."

  # Use Homebrew to install WireGuard
  brew install wireguard-tools
}

# Function to generate WireGuard keys
generate_keys() {
  echo "Generating WireGuard keys..."

  # Generate private key
  PRIVATE_KEY=$(wg genkey)

  # Generate public key from the private key
  PUBLIC_KEY=$(echo "$PRIVATE_KEY" | wg pubkey)

  # Output the keys
  echo "Private Key: $PRIVATE_KEY"
  echo "Public Key: $PUBLIC_KEY"
}

# Check the operating system
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
  # Linux
  if ! command_exists wg; then
    install_wireguard_linux
  fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS
  if ! command_exists wg; then
    install_wireguard_mac
  fi
else
  echo "Unsupported OS: $OSTYPE"
  exit 1
fi

# Generate and output keys
generate_keys
