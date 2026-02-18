#ifndef MAGIC_SQUARE_SOLVER_HPP
#define MAGIC_SQUARE_SOLVER_HPP

#include <set>
#include <string>
#include <utility>
#include <vector>

#include "json_parser.hpp"

namespace msolver {

struct Request {
  int target = 0;
  int size = 0;
  std::vector<std::vector<int>> known_grid;
  std::string game_mode = "unbounded";
  std::string solve_method = "mrv_backtracking";
};

struct State {
  int target;
  int size;
  int max_val;
  std::vector<std::vector<int>> grid;
  std::vector<int> row_sums;
  std::vector<int> col_sums;
  std::vector<int> row_unknowns;
  std::vector<int> col_unknowns;
  std::vector<int> diag_sums;
  std::vector<int> diag_unknowns;
  std::set<int> used;
  std::vector<std::pair<int, int>> unknowns;
};

Request parse_request(const JsonValue &root);
State build_state(const Request &req);
bool solve_state(State &st, const std::string &solve_method);
std::string render_solution_json(const State &st);

}  // namespace msolver

#endif
