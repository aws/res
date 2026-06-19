package util

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
)

func baseConfig() map[string]string {
	return map[string]string{
		"aws_region":            "us-east-1",
		"aws_access_key_id":     "",
		"aws_secret_access_key": "",
	}
}

func TestAwsConfigWithValidProfile(t *testing.T) {
	tmpDir := t.TempDir()
	configFile := filepath.Join(tmpDir, "config")
	content := "[profile test_profile]\nregion = us-east-1\n"
	err := os.WriteFile(configFile, []byte(content), 0644)
	assert.NoError(t, err)

	cfg := baseConfig()
	cfg["aws_profile"] = "test_profile"
	cfg["aws_config_file"] = configFile

	result, err := awsConfig(cfg)
	assert.NoError(t, err)
	assert.Equal(t, "us-east-1", result.Region)
}

func TestAwsConfigWithEmptyProfileFallsThrough(t *testing.T) {
	cfg := baseConfig()
	cfg["aws_profile"] = ""

	result, err := awsConfig(cfg)
	assert.NoError(t, err)
	assert.Equal(t, "us-east-1", result.Region)
}

func TestAwsConfigWithoutProfileKeyFallsThrough(t *testing.T) {
	cfg := baseConfig()

	result, err := awsConfig(cfg)
	assert.NoError(t, err)
	assert.Equal(t, "us-east-1", result.Region)
}

func TestAwsConfigProfileBranchErrorIncludesProfileName(t *testing.T) {
	tmpDir := t.TempDir()
	configFile := filepath.Join(tmpDir, "config")
	err := os.WriteFile(configFile, []byte("[default]\nregion = us-east-1\n"), 0644)
	assert.NoError(t, err)

	cfg := baseConfig()
	cfg["aws_profile"] = "nonexistent_profile"
	cfg["aws_config_file"] = configFile

	_, err = awsConfig(cfg)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "nonexistent_profile")
	assert.Contains(t, err.Error(), "Unable to load the AWS SDK config with profile")
}
