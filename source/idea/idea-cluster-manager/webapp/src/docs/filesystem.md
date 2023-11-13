## File Systems

Create and manage file systems for the environment. File System providers currently supported on RES are:

-   Amazon EFS
-   Amazon FSx for NetApp ONTAP

### Create a new File System

Click **Create File System** button to create a new File System.

#### Amazon EFS

Provide private subnets in two different AZs to create mount targets. For more details see [managing mount targets for Amazon EFS](https://docs.aws.amazon.com/efs/latest/ug/manage-fs-access.html)

#### Amazon FSx for NetApp ONTAP

Provide primary private subnet id for Single-AZ.

Provide primary and stand-by private subnet ids for Multi-AZ file system.

For more details see [network resources for Multi-AZ FSx Netapp ONTAP](https://docs.aws.amazon.com/fsx/latest/ONTAPGuide/high-availability-AZ.html#single-multi-az-resources)

_Note: Please wait for the file system to be in available state before launching VDI._

### Add File System to Project

Select your file system and click **Actions** > **Add File System To Project**
You can add your file system to an existing RES project. New VDI instances launched in the project will mount the added file system.

### Remove File System from Project

Select your file system and click **Actions** > **Remove File System From Project**
You can remove your file system from an existing RES project. New VDI instances launched in the project will not mount the removed file system.
