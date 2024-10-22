package util

import (
	"fmt"
	"log"
	"log/syslog"
)

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
