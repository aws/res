## License Resources

Create scheduler resources for your floating/network licenses.

### Create a new license resource

Click **Create License Resource** to initiate a new resource creation. You will have to specify the following parameters:

#### Title

A Friendly name for your own records

#### Resource Name

The actual scheduler resource name. It must use the following format **{app}\_lic\_{feature}**.

> Once created, you will be able to use it via **qsub -l {app}\_lic\_{feature}=<number_of_tokens>**

#### Reserved Licenses

Specify the number of licenses to be reserved for non-HPC usage.

#### Availability Check Script

Script to retrieve the number of licenses available. IDEA provides a basic example (license_checks.py). You can extend it or create new script to match your own requirements. The output of the script must be an integer.

### Edit a license resource

Select the license resource you want to edit then click **Actions** > **Edit License Resource**
