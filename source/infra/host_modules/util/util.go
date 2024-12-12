package util

import (
	"crypto/sha256"
	"fmt"
	"log"
	"log/syslog"
	"math/big"
	"strconv"
	"strings"
)

func getHashBetween(s string, min uint64, max uint64) (uint64, error) {
	// Hash string
	hasher := sha256.New()
	hasher.Write([]byte(s))
	b := hasher.Sum(nil)

	// Convert hash to big int and return it between min and max
	bi := new(big.Int).SetBytes(b)
	return min + (uint64(bi.Int64()) % (max - min)), nil
}

func convertToBase27(str string, min uint64, max uint64)(uint64, error) {
	const base = 27
	var result uint64

	for _, r := range strings.ToLower(str) {
		var digit int
		switch {
		case r >= 'a' && r <= 'z':
			digit = int(r-'a') + 1
		default:
			return 0,  fmt.Errorf("Invalid character in string") // Invalid character in the string
		}
		result = result * base + uint64(digit)
	}

    // Subtract by 1 since smallest value for result is 1, and `min` is the minimum valid id
    var updatedResult uint64 = result + (min - 1)

    if updatedResult > max {
        return 0, fmt.Errorf("Value id of %d is larger than max value %d",  updatedResult, max)
    }

	return updatedResult, nil
}

func GetGroupHash(config map[string]string, name string) (uint64, error) {

	idMin_s, exists := config["min_id"]
	if !exists {
		return 0, fmt.Errorf("Unable to determine the minimum UID.")
	}
	idMin, err := strconv.ParseUint(idMin_s, 10, 64)
	if err != nil || idMin < 1000 {
		return 0, fmt.Errorf("Value for minimum UID is invalid: %s", idMin_s)
	}

	idMax_s, exists := config["max_id"]
	if !exists {
		return 0, fmt.Errorf("Unable to determine the maximum UID.")
	}

	idMax, err := strconv.ParseUint(idMax_s, 10, 64)
	if err != nil || idMax < 1000 || idMax <= idMin {
		return 0, fmt.Errorf("Value for maximum UID is invalid: %s", idMin_s)
	}

	return convertToBase27(name, idMin, idMax)
}

func Logf(tag string, msg string, args ...interface{}) {
	formatted := fmt.Sprintf(msg, args...)

	sysLog, err := syslog.New(syslog.LOG_INFO, tag)
	if err == nil && sysLog != nil {
		// Log to syslog if no error
		defer sysLog.Close()
		sysLog.Info(formatted)
	} else {
		// Fallback to standard output
		log.Println(formatted)
	}
}
