# Virtual Machine README

This file will describe how to go about installing and using a virtual machine running Ubuntu 18.04 in order to run MeMS in the same environment as production and guarantee code will work as expected.

## Clone this repository
If you have not already, clone this repository to your computer. The --recursive param is necessary in order to have git fetch the submodules the project needs alongside the primary code.
> git clone --recursive git@github.com:bastmaleexcel/mems.git

If you already cloned the repo and didn't add the --recursive command, you can run the following to get the submodules.
> git submodule update --init --recursive


## Download Ubuntu
You will need a copy of the Ubuntu Server ISO to setup your virtual machine, you can download it directly from [Ubuntu](https://releases.ubuntu.com/18.04/ubuntu-18.04.4-live-server-amd64.iso). Store it somewhere you can find it later.

## Download and Install VirtualBox
First download the appropriate version for your OS. All versions can be found on the [VirtualBox](https://www.virtualbox.org/wiki/Downloads) download page.

Installation process will be different based on your OS, but shouldn't require any information to complete.

### Setup Host Network
In order to easily access the network of the VM we need to add a Host Network to VirtualBox. You do this by clicking on the **File menu** and selecting **Host Network Manager...**

In the Host Network Manager dialog click on the Create button in the top left. A default network of 192.168.56.1/24 should be created with the name vboxnet0. You can now close the manager dialog.

## Create the VM
Once VirtualBox is installed, run it and you should be presented with a window welcoming you to VirtualBox with some buttons above the message. Look for the blue star-like icon with **New** under it. Click this to start the process of creating the blank VM.

### Name and Operating System
* You can **Name** the VM anything you want, it's not important, but I suggest "MeMS" to make it easy to find.
* There is no need to change the **Machine Folder** value, but if you lack space on your primary drive it's a good idea to place this somewhere you can handle approx 12gb of data.
* Set the **Type** to Linux
* Set the **Version** to Ubuntu (64-bit)

### Memory Size
At bare minimum 1024mb will run, but I recommend 2048mb+ in order to keep the VM from struggling to run everything.

### Hard disk
Stay with the default "Create a virtual hard disk now" and click Create.

### Hard disk file type
Stay with the default "VDI (VirtualBox Disk Image)" and click Next>.

### Storage on physical hard disk
Stay with the default "Dynamically allocated" and click Next>.

### File location and size
10gb should be absolutely fine, I don't recommend changing this unless you're really strapped for space, in which case don't go below 7gb. There is no reason to go above 10gb. Click Create when you're done.

## Setup VM
Now that your VM is created it should show up in the list on VirtualBox and be auto-selected. Click on the orange/yellow gear marked **Settings** to get started.

### Network
In order to use the host network we created previously:
* Click on the Network item in the left hand side menu
* Click on Adapter 2
* Check the **Enable Network Adapter** checkbox
* Set **Attached to** to *Host-only Adapter*
* **Name** should auto-select *vboxnet0* that we previously created

### Shared Folders
* Click on the Shared Folders item in the left hand side menu
* Click on the little blue folder with the green + on the right hand side
* Set **Folder Path** to the folder you cloned the repository into
* Rename the **Folder Name** to "share" as this will be used in a future step and because VBox has had known issues in the past with the share name being the same as the folder name
* Ignore the other options and click the OK button
* OK again to get out of settings

## Install Ubuntu
Now that your VM is created and the settings done, we can start the Linux install process. Double click on the VM, or click on the Start button to the top right.

### Select start-up disk
Now you need to find the ISO image you downloaded in the **Download Ubuntu** step. Make sure it's selected and click on the Start button.

### Install Steps
#### Initial
* English
* Update to the new installer
* Done
* Done
* Done
* Done
* Use an entire disk. Done
* Done
* Continue

#### Profile Setup
Obviously you can set these to whatever you want, but if you forget what they are, you're on your own.
* **Your Name**: mems
* **Your server's name**: mems
* **Pick a username**: mems
* **Pick a password**: mems
* **Confirm your password**: mems
* select Done

#### SSH Setup
It'll be a lot easier to access this machine via SSH as you can't copy/paste into the regular VM window, so I highly recommend this step. Check the **Install OpenSSH server** check and select Done.

#### Featured  Server Snaps
We don't need anything, just select Done

#### Reboot
Once Ubuntu is down installing and updating, select Reboot. Don't worry about the messaging saying to remove media, just hit enter and allow the VM to reboot.

## Setup Ubuntu
Now that ubuntu is running, login as mems/mems and then
> sudo su -

in order to give yourself superuser access.

### Install Guest Additions
This will allow you to attach the shared folder with full rights.
* `apt install make gcc`
* In the menu, click **Devices**
* Select **Insert Guest Additions CD image**
* `mount /dev/cdrom /media`
* `/media/VBoxLinuxAdditions.run`
* `reboot`

### Add Shared Folder
* login as mems/mems
* `sudo su -`
* `cd /`
* `mkdir /mems`
* `echo 'vboxsf' | tee -a /etc/modules`
* `echo 'share /mems vboxsf uid=0,gid=0,umask=0000,_netdev 0 0' | tee -a /etc/fstab`
* `mount share`

### Set host-only IP
Now that the share is mounted, you can set the IP address
* `/mems/install/host_only.sh`

### Allow Root Access
Auto log the VM into root, as well as allowing root access via SSH. I suggest using the password mems
* `/mems/install/root_access.sh`
* `shutdown -P now`

## Snapshot the VM
Because things can always go wrong, it's a good idea at this point, before we install the software for MeMS, to take a snapshot of the VM in case there are any issues. This will help avoid having to redo all the previous steps if your VM somehow gets corrupted or the process fails halfway through, which I've had happen if I suddenly lose internet access.
* In the VM Manager, click on your VM instance
* Now click on **Take** and give the snapshot a name. I usually use "ga + root" for Guest Additions plus root access.

## Install MeMS
Once the VM reboots you should now be auto-logged in as root and be able to install the necessary software to get MeMS up and running as a dev environment.
If you plan to connect to an external server to get MySQL/Redis access, then you can answer no to the first question, but be sure to answer yes to the second question in order to setup nginx with a local certificate and dev domain names.
* `cd /mems`
* `./install.sh`
* `reboot`

## Install MySQL Tables
If you said yes to the first part of the install and have installed MySQL locally for development, or you are connecting to an external MySQL that hasn't been setup yet, you will need to install the schemas and tables.
* `src_mems`
* `python install.py`

## Add Hostname
In order to be able to access the services via Postman or a browser, you will need to add the hostname to your hosts file. This location of this file is different depending on your OS, I suggest [the following article](https://www.howtogeek.com/howto/27350/beginner-geek-how-to-edit-your-hosts-file/) for finding and editting your hosts file. Once you've found it, add the following line to it
> 192.168.56.30 mems.local

## Supervisor
The services within MeMS run through a process control system called [Supervisor](http://supervisord.org/). You can access supervisor directly through your VM using:

Get status of services
* `supervisorctl`

Restart auth service
* `supervisorctl restart auth`

Restart all services
* `supervisorctl restart all`

Or via a browser UI by connecting to:
* http://mems.local:9001
user: mems
pass: mems
