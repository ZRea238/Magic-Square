package main

import (
	"fmt"
	"os"
)

func fail(message string) {
	_, _ = fmt.Fprintln(os.Stderr, message)
	os.Exit(1)
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func diagIndexes(r, c, size int) []int {
	indexes := []int{}
	if r == c {
		indexes = append(indexes, 0)
	}
	if r+c == size-1 {
		indexes = append(indexes, 1)
	}
	return indexes
}

func minMaxSum(values []int, count int) (int, int) {
	if count == 0 {
		return 0, 0
	}
	if len(values) < count {
		return 1, 0
	}
	minSum := 0
	maxSum := 0
	for i := 0; i < count; i++ {
		minSum += values[i]
		maxSum += values[len(values)-1-i]
	}
	return minSum, maxSum
}
