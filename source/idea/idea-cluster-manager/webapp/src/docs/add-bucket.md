## Add bucket

Add a S3 bucket to Research and Engineering Studio (RES). Currently only available for Linux desktops. Mounting S3 buckets on Windows desktops is not supported.

### Bucket setup

Required to provide a display name, ARN, mount point, and mode for the bucket.

When setting the bucket to read and write mode (R/W), a custom prefix may be provided that will create directories depending upon either the project ID, or the project ID and user ID.

For cross-account access, provide a IAM role ARN with the necessary permissions to mount the bucket onto the Virtual Desktop. Refer to the AWS Research and Engineering Studio Administrator guide for further details.

### Project association

Associate the bucket with projects in Research and Engineering Studio (RES). You can create new projects on the Projects page found under the Environment Management section of Research and Engineering Studio (RES).
 
Note that buckets will not automatically mount to already provisioned VDI sessions. Associate a bucket with a project prior to launching VDIs in that project.

### Additional information

For additional information, see the [S3 buckets](https://docs.aws.amazon.com/res/latest/ug/S3-buckets.html) section in the official AWS documentation for Research and Engineering Studio (RES).
