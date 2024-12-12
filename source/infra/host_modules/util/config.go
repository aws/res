package util

import (
	"bufio"
	"os"
	"strings"
)

type Config map[string]string

const defaultPath = "/etc/cognito_auth.conf"

func ParseConfig() (Config, error) {
	config := make(Config)

	configPath := os.Getenv("CONFIG_PATH")
	if configPath == "" {
		configPath = defaultPath
	}

	file, err := os.Open(configPath)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := scanner.Text()
		if equal := strings.Index(line, "="); equal >= 0 {
			if key := strings.TrimSpace(line[:equal]); len(key) > 0 {
				value := ""
				if len(line) > equal {
					value = strings.TrimSpace(line[equal+1:])
				}
				envValue := os.Getenv(strings.ToUpper(key))
				if envValue == "" {
					config[key] = value
				} else {
					config[key] = envValue
				}
			}
		}
	}

	if err := scanner.Err(); err != nil {
		return nil, err
	}

	return config, nil
}
