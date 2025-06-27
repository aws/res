function Download-And-Execute-Script {
    param (
        [string]$uri,
        [string]$arguments = "",
        [string]$launchScriptsPath = ".\launch\scripts"
    )

    # Create directory if it doesn't exist
    if (-not (Test-Path -Path $launchScriptsPath)) {
        New-Item -ItemType Directory -Path $launchScriptsPath -Force | Out-Null
    }
    $fileName = Split-Path $uri -Leaf
    $destination = Join-Path $launchScriptsPath $fileName

    $timestamp = Get-Date -Format 'yyyyMMddTHHmmssffffZ'
    $DownloadAndExecuteScript = "$env:SystemDrive\Users\Administrator\RES\Bootstrap\Log\DownloadAndExecuteScript.$fileName.log.$timestamp"

    Start-Transcript -Path $DownloadAndExecuteScript -NoClobber -IncludeInvocationHeader

    if ($uri -like "s3://*") {
        $urlParts = $uri -split "/", 4
        $bucketName = $urlParts[2]
        $key = $urlParts[3]
        $fullPath = (Resolve-Path -Path $launchScriptsPath).Path
        $destination = Join-Path $fullPath (Split-Path $uri -Leaf)
        Copy-S3Object -BucketName $bucketName -Key $key -LocalFile $destination -Force
    }
    elseif ($uri -like "https://*") {
        Invoke-WebRequest -Uri $uri -OutFile $destination
    }
    elseif ($uri -like "file://*") {
        $filePath = $uri -replace "file://"
        Copy-Item -Path $filePath -Destination $destination
    }
    else {
        Write-Output "Unsupported URI format: $uri"
        exit 1
    }

    # Make the downloaded script executable
    Set-ItemProperty -Path $destination -Name IsReadOnly -Value $false

    # Execute the downloaded script
    Invoke-Expression "$destination $arguments"

    # Remove the downloaded script
    Remove-Item $destination

    Stop-Transcript
}
