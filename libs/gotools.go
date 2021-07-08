package main

import "C"

import (
	"time"
)

//export ParseDuration
func ParseDuration(s string) (int64, int) {

	r, e := time.ParseDuration(s)

	if e != nil {
		return 0, 1
	} else {
		return int64(r), 0
	}

}

func main() {}
