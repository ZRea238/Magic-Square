package main

import "math/rand"

type Request struct {
	Target      int       `json:"target"`
	Size        int       `json:"size"`
	KnownGrid   [][]*int  `json:"known_grid"`
	GameMode    string    `json:"game_mode"`
	SolveMethod string    `json:"solve_method"`
	Language    string    `json:"language"`
}

type Response struct {
	Solution [][]int `json:"solution"`
}

type State struct {
	grid         [][]int
	target       int
	size         int
	maxVal       int
	rowSums      []int
	colSums      []int
	rowUnknowns  []int
	colUnknowns  []int
	diagSums     [2]int
	diagUnknowns [2]int
	used         map[int]bool
	unknowns     [][2]int
	rng          *rand.Rand
}
