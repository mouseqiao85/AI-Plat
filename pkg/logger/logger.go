package logger

import (
	"log"
	"os"
)

type Logger struct {
	*log.Logger
	level string
}

func New(level, format string) *Logger {
	l := &Logger{
		Logger: log.New(os.Stdout, "", log.LstdFlags|log.Lshortfile),
		level:  level,
	}
	return l
}

func (l *Logger) Info(format string, v ...interface{}) {
	l.Printf("[INFO] "+format, v...)
}

func (l *Logger) Debug(format string, v ...interface{}) {
	if l.level == "debug" {
		l.Printf("[DEBUG] "+format, v...)
	}
}

func (l *Logger) Error(format string, v ...interface{}) {
	l.Printf("[ERROR] "+format, v...)
}

func (l *Logger) Warn(format string, v ...interface{}) {
	l.Printf("[WARN] "+format, v...)
}
