# indigo-netdev

Represents devices on the network, such as computers or other connected devices.

## Requirements

[Indigo Pro](https://www.indigodomo.com) is required to get support for plugins.  If you
haven't tried Indigo and are interested in home automation, please give it a shot right
away...  You won't be disappointed!

To communicate with remote devices, this plugin depends on the `ssh` command locally.  It
must be executable by the user running the Indigo server to function properly.

Additionally, this plugin requires Indigo 7 or higher.

## Installation

This plugin is installed like any other Indigo plugin.  Visit the
[releases](https://github.com/jheddings/indigo-rtoggle/releases) page and download the
latest version.  For advanced users, you may also clone the source tree directly into your
Indigo plugins folder, making updates as easy as pull & reload.

## Configuration

After installing the first time, you will be prompted for the plugin configuration.  You
can also access the plugin config at any time from the Plugins menu in Indigo.

The "Refresh Interval" determines how often Indigo will poll your network devices for
status (in seconds).  This value should be something reasonable that your network and
remote systems can tolerate.  Note that some systems get unhappy if they are polled too
often, which may result in blocking your IP address.  Values for this option range from
1 to 3600 (1 hour) seconds.

Specifying the "Connection Timeout" establishes how long the plugin will wait for a remote
system to respond before considering it unreachable.  This value should be small enough to
keep things responding quickly, but long enough to account for any network latencies or
system performance variations.

### Network Service

Network services are monitored by performing a basic check on the supplied port.  This is
usefuly to get a quick status for remote systems when the service itself is less important.

These device support status only.

### Ping Status

Pings an address and reports 'Active' if it responds succesfully.

### HTTP Status

Examine the HTTP status of a path and set device as OK or ERROR.

### External IP

Querries [ipify](https://www.ipify.org) for the current external IP (either IPv4 or IPv6).

### Local Devices

Uses the local ARP table to find devices on the network by their hardware or MAC address.

*NOTE* this device type depends on the `arp` command.  You can see the active devices by
running `arp -a` on your Indigo server to troubleshoot issues.  Due to different network
configurations and routers, some wireless devices may not be seen on a wired network.  In
this case, joining the wireless network on the Indigo server may help.

### SSH Server

All SSH commands are authenticated using a shared keypair.  This must be generated and
available for the local Indigo user (typicall in the local user's .ssh folder).  Here
is a [basic overview](https://www.debian.org/devel/passwordlessssh) for setting up SSH keys.

When checking status, the SSH server will use a safe command (`true` by default) to
determine whether the system is off or on.  The exit code is also examined to ensure the
command completed succesfully.  This has a few interesting side effects, namely that this
will ensure SSH is responding correctly and any errors running the command are seen as
the device being "off."

SSH Devices may be turned off like an Indigo relay device.  The advanced configuration in
the device configuration allows the user to set a specific command to safely shut down as
if running on the command line.  Some devices, such as routers or other embedded linux
servers, use the `poweroff` command rather than `shutdown`.

The "Username" property will be passed to the SSH client to authenticate on the remote
system.  If this is left blank, the Indigo server user will be used.  For most applications,
this value will be set to the super user account (e.g. "root") to enable shutting down the
system from the command line.

*NOTE* once turned off, these devices must be turned on at the system.

## Usage

Once devices are configured, their state may be monitored for triggers.  Servers and devices
that support Indigo's relay features may be acted upon as any other device.
