## Virtual Desktops

Manage your Windows & Linux virtual desktops, powered by [Amazon DCV](https://aws.amazon.com/hpc/dcv/).

<details>
    <summary markdown="span"><b>Create a new desktop</b></summary>

Click **"Launch New Virtual Desktop"** and follow the instructions to create your virtual desktop.

</details>

<details>
    <summary markdown="span"><b>Access your desktop</b></summary>

You can access your virtual desktop directly within your browser by clicking **"Connect"** button.

> **Note:** For best performance, we recommend using DCV native application. Click **"?"** button to learn more.

</details>

<details>
    <summary markdown="span"><b>Desktop Lifecycle</b></summary>

Click **"Actions"** > **"Virtual Desktop State"** to manage your virtual desktop session:

-   **Start:** Start a stopped session
-   **Stop:** Stop a running session (EBS storage is preserved)
-   **Reboot:** Reboot your session
-   **Hibernate:** If applicable, RES will hibernate your session and save all content in memory. Processes will automatically be resumed when you restart your session.
-   **Terminate:** Terminate your session. Attention, this will release the hardware and your session will be gone. Storage might be lost if you are not using a persistent file system such as EFS or FSx

</details>

<details>
    <summary markdown="span"><b>Update desktop compute</b></summary>

You can change the EC2 instance associated to your virtual desktop at any moment. To upgrade/downgrade your hardware:

-   Stop your Virtual Desktop
-   Click **"Actions"**
-   Click **"Update Session"**

From there, choose your new EC2 instance type and restart your Virtual Desktop.

</details>

<details>
    <summary markdown="span"><b>Configure schedule</b></summary>

Setup a schedule to start/stop your virtual desktop to save and manage costs.

> **Note:** Virtual Desktop will only be stopped if there is no active DCV client connected for 2 hours and the overall CPU usage is below a certain threshold. Idle time/CPU threshold are configurable by Admins. This measure is meant to prevent Virtual Desktop to be accidentally stopped while running simulations.

-   **No Schedule**: Virtual Desktop lifecycle are managed by the user. Active session will run until you manually stop/terminate it. Stopped session will stay stopped until you manually start it. This is the default scheduling mode
-   **Working Hours**: RES will automatically start your session in the morning and stop it if inactive in the evening. Hours can be configured by RES admins
-   **Stop All Days**: Enforce session to be stopped all day. If you manually start your session, RES will automatically stop it after the idle period configured by admins
-   **Start All Days**: Enforce session to be started all day. If you manually stop your session, RES will automatically start it.
-   **Custom Schedule**: User defines when the session must be started/stopped

</details>
