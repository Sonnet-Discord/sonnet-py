package main

import "C"

import (
	"bufio"
	"bytes"
	"errors"
	"io"
	"os"
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

// Readfile
func readfile(f string) ([]byte, error, bool) {

	fp, err := os.Open(f)
	defer fp.Close()

	if err != nil {
		return nil, err, true
	}

	var flen int64

	if stat, err := fp.Stat(); err == nil {
		flen = stat.Size()
	}

	// 32 bit overflow
	if int64(int(flen)) != flen {
		return nil, errors.New("RAM not large enough to store file"), false
	}

	if flen == 0 {

		// Let go stdlib handle reallocs on this
		var builder bytes.Buffer
		alloc := make([]byte, 1024)

		for {

			i, err := fp.Read(alloc)

			if err != nil {
				if err == io.EOF {
					builder.Write(alloc[:i])
					break
				} else {
					return nil, err, false
				}
			} else {
				builder.Write(alloc[:i])
			}

		}

		return builder.Bytes(), nil, false

	} else {

		sab := make([]byte, flen)

		i, err := fp.Read(sab)

		return sab[:i], err, false

	}

}

func valid(s []byte) bool {

	if len(s) > 85 || len(s) < 1 {
		return false
	}

	for i, _ := range s {
		if !('0' <= s[i] && s[i] <= 'z') {
			return false
		}
	}
	return true
}

//export GenerateCacheFile
func GenerateCacheFile(fin, fout string) int {

	buf, err, nexist := readfile(fin)

	if err != nil {
		if nexist {
			return 2
		} else {
			return 1
		}
	}

	slices := bytes.Split(buf, []byte{'\n'})

	filter := slices[:0]

	var maxlen int

	for i, _ := range slices {
		if valid(slices[i]) {
			if 'a' <= slices[i][0] && slices[i][0] <= 'z' {
				slices[i][0] -= 'a' - 'A'
			}

			if len(slices[i]) > maxlen {
				maxlen = len(slices[i])
			}

			filter = append(filter, slices[i])
		}
	}

	fp, err := os.Create(fout)
	defer fp.Close()

	if err != nil {
		return 1
	}

	writebuffer := make([]byte, maxlen)
	nilbuffer := make([]byte, maxlen)

	// ++ for the length prefix
	maxlen++

	writer := bufio.NewWriter(fp)

	werr := writer.WriteByte(byte(maxlen))

	if werr != nil {
		return 1
	}

	for i, _ := range filter {

		copy(writebuffer, nilbuffer)
		copy(writebuffer, filter[i])

		werr := writer.WriteByte(byte(len(filter[i])))

		if werr != nil {
			return 1
		}

		_, werr = writer.Write(writebuffer)

		if werr != nil {
			return 1
		}

	}

	ferr := writer.Flush()

	if ferr != nil {
		return 1
	}

	return 0
}

func main() {}
