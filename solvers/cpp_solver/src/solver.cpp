#include "solver.hpp"

#include <algorithm>
#include <chrono>
#include <random>
#include <stdexcept>

namespace msolver {

static std::vector<int> diag_indexes(int r, int c, int size) {
  std::vector<int> idx;
  if (r == c) idx.push_back(0);
  if (r + c == size - 1) idx.push_back(1);
  return idx;
}

static std::pair<int, int> min_max_sum(const std::vector<int> &values, int count) {
  if (count == 0) return {0, 0};
  if ((int)values.size() < count) return {1, 0};
  int mn = 0;
  int mx = 0;
  for (int i = 0; i < count; i++) {
    mn += values[i];
    mx += values[(int)values.size() - 1 - i];
  }
  return {mn, mx};
}

static std::vector<int> remaining_available(const State &st, int exclude) {
  std::vector<int> values;
  for (int v = 1; v <= st.max_val; v++) {
    if (st.used.find(v) != st.used.end()) continue;
    if (v == exclude) continue;
    values.push_back(v);
  }
  return values;
}

static std::pair<int, int> value_bounds(const State &st, int r, int c) {
  int row_left = st.target - st.row_sums[r];
  int col_left = st.target - st.col_sums[c];
  std::vector<int> exact_values;
  std::vector<int> upper_candidates;

  if (st.row_unknowns[r] == 1) exact_values.push_back(row_left);
  else upper_candidates.push_back(row_left - (st.row_unknowns[r] - 1));

  if (st.col_unknowns[c] == 1) exact_values.push_back(col_left);
  else upper_candidates.push_back(col_left - (st.col_unknowns[c] - 1));

  for (int d : diag_indexes(r, c, st.size)) {
    int diag_left = st.target - st.diag_sums[d];
    int diag_unknown = st.diag_unknowns[d];
    if (diag_unknown == 1) exact_values.push_back(diag_left);
    else upper_candidates.push_back(diag_left - (diag_unknown - 1));
  }

  if (!exact_values.empty()) {
    int ref = exact_values[0];
    if (ref < 1) return {1, 0};
    for (int v : exact_values) {
      if (v != ref) return {1, 0};
    }
    for (int upper : upper_candidates) {
      if (ref > upper) return {1, 0};
    }
    return {ref, ref};
  }

  if (upper_candidates.empty()) return {1, 0};
  int upper = *std::min_element(upper_candidates.begin(), upper_candidates.end());
  return {1, upper};
}

static bool can_place(const State &st, int value, int r, int c) {
  if (st.used.find(value) != st.used.end()) return false;

  int row_remaining_unknown = st.row_unknowns[r] - 1;
  int col_remaining_unknown = st.col_unknowns[c] - 1;

  int row_after = st.row_sums[r] + value;
  int col_after = st.col_sums[c] + value;

  int row_remaining_sum = st.target - row_after;
  int col_remaining_sum = st.target - col_after;

  if (row_remaining_unknown == 0 && row_remaining_sum != 0) return false;
  if (col_remaining_unknown == 0 && col_remaining_sum != 0) return false;

  std::vector<int> remaining = remaining_available(st, value);
  if (row_remaining_unknown > 0) {
    auto mm = min_max_sum(remaining, row_remaining_unknown);
    if (row_remaining_sum < mm.first || row_remaining_sum > mm.second) return false;
  }
  if (col_remaining_unknown > 0) {
    auto mm = min_max_sum(remaining, col_remaining_unknown);
    if (col_remaining_sum < mm.first || col_remaining_sum > mm.second) return false;
  }

  for (int d : diag_indexes(r, c, st.size)) {
    int diag_remaining_unknown = st.diag_unknowns[d] - 1;
    int diag_after = st.diag_sums[d] + value;
    int diag_remaining_sum = st.target - diag_after;

    if (diag_remaining_unknown == 0 && diag_remaining_sum != 0) return false;
    if (diag_remaining_unknown > 0) {
      auto mm = min_max_sum(remaining, diag_remaining_unknown);
      if (diag_remaining_sum < mm.first || diag_remaining_sum > mm.second) return false;
    }
  }

  return true;
}

static std::vector<int> valid_candidates(State &st, int r, int c, bool randomized) {
  auto bounds = value_bounds(st, r, c);
  int low = bounds.first;
  int high = std::min(bounds.second, st.max_val);
  if (low > high) return {};

  std::vector<int> candidates;
  for (int v = low; v <= high; v++) {
    if (can_place(st, v, r, c)) candidates.push_back(v);
  }
  if (randomized && candidates.size() > 1) {
    static unsigned seed = (unsigned)std::chrono::high_resolution_clock::now().time_since_epoch().count();
    std::shuffle(candidates.begin(), candidates.end(), std::default_random_engine(seed));
  }
  return candidates;
}

struct Choice {
  int r = -1;
  int c = -1;
  std::vector<int> candidates;
  bool has = false;
};

static Choice select_next(State &st, bool randomized) {
  Choice best;
  int best_domain = -1;

  for (auto &pos : st.unknowns) {
    int r = pos.first;
    int c = pos.second;
    if (st.grid[r][c] != 0) continue;

    std::vector<int> cands = valid_candidates(st, r, c, randomized);
    if (cands.empty()) {
      return Choice{r, c, {}, true};
    }
    if (best_domain == -1 || (int)cands.size() < best_domain) {
      best_domain = (int)cands.size();
      best.r = r;
      best.c = c;
      best.candidates = cands;
      best.has = true;
    }
  }

  return best;
}

static Choice select_next_exhaustive(State &st, bool randomized) {
  for (auto &pos : st.unknowns) {
    int r = pos.first;
    int c = pos.second;
    if (st.grid[r][c] != 0) continue;
    std::vector<int> cands = valid_candidates(st, r, c, randomized);
    return Choice{r, c, cands, true};
  }
  return Choice{};
}

static void apply_value(State &st, int value, int r, int c) {
  st.grid[r][c] = value;
  st.row_sums[r] += value;
  st.col_sums[c] += value;
  st.row_unknowns[r]--;
  st.col_unknowns[c]--;
  for (int d : diag_indexes(r, c, st.size)) {
    st.diag_sums[d] += value;
    st.diag_unknowns[d]--;
  }
  st.used.insert(value);
}

static void revert_value(State &st, int value, int r, int c) {
  st.grid[r][c] = 0;
  st.row_sums[r] -= value;
  st.col_sums[c] -= value;
  st.row_unknowns[r]++;
  st.col_unknowns[c]++;
  for (int d : diag_indexes(r, c, st.size)) {
    st.diag_sums[d] -= value;
    st.diag_unknowns[d]++;
  }
  st.used.erase(value);
}

static bool final_constraints(const State &st) {
  for (int i = 0; i < st.size; i++) {
    if (st.row_sums[i] != st.target || st.col_sums[i] != st.target) return false;
  }
  return st.diag_sums[0] == st.target && st.diag_sums[1] == st.target;
}

static bool search(State &st, bool propagation, bool randomized, bool exhaustive) {
  std::vector<std::tuple<int, int, int>> forced;

  while (true) {
    Choice choice = exhaustive ? select_next_exhaustive(st, randomized) : select_next(st, randomized);
    if (!choice.has) return final_constraints(st);

    if (choice.candidates.empty()) {
      for (int i = (int)forced.size() - 1; i >= 0; i--) {
        auto [r, c, v] = forced[i];
        revert_value(st, v, r, c);
      }
      return false;
    }

    if (!propagation || choice.candidates.size() != 1) {
      for (int value : choice.candidates) {
        apply_value(st, value, choice.r, choice.c);
        if (search(st, propagation, randomized, exhaustive)) return true;
        revert_value(st, value, choice.r, choice.c);
      }
      for (int i = (int)forced.size() - 1; i >= 0; i--) {
        auto [r, c, v] = forced[i];
        revert_value(st, v, r, c);
      }
      return false;
    }

    int forced_value = choice.candidates[0];
    apply_value(st, forced_value, choice.r, choice.c);
    forced.push_back(std::make_tuple(choice.r, choice.c, forced_value));
  }
}

Request parse_request(const JsonValue &root) {
  if (root.type != JsonValue::Object) throw std::runtime_error("request root must be object");

  Request req;
  auto get_number = [&](const std::string &k) -> int {
    auto it = root.object.find(k);
    if (it == root.object.end() || it->second.type != JsonValue::Number) throw std::runtime_error("missing numeric field: " + k);
    return (int)it->second.number;
  };

  req.target = get_number("target");
  req.size = get_number("size");

  auto gm = root.object.find("game_mode");
  if (gm != root.object.end() && gm->second.type == JsonValue::String) req.game_mode = gm->second.str;

  auto sm = root.object.find("solve_method");
  if (sm != root.object.end() && sm->second.type == JsonValue::String) req.solve_method = sm->second.str;

  req.known_grid.assign(req.size, std::vector<int>(req.size, 0));
  auto kg = root.object.find("known_grid");
  if (kg != root.object.end() && kg->second.type == JsonValue::Array) {
    if ((int)kg->second.array.size() != req.size) throw std::runtime_error("known_grid shape mismatch");
    for (int r = 0; r < req.size; r++) {
      const JsonValue &row = kg->second.array[r];
      if (row.type != JsonValue::Array || (int)row.array.size() != req.size) throw std::runtime_error("known_grid shape mismatch");
      for (int c = 0; c < req.size; c++) {
        if (row.array[c].type == JsonValue::Null) {
          req.known_grid[r][c] = 0;
        } else if (row.array[c].type == JsonValue::Number) {
          req.known_grid[r][c] = (int)row.array[c].number;
        } else {
          throw std::runtime_error("known_grid values must be number or null");
        }
      }
    }
  }

  return req;
}

State build_state(const Request &req) {
  if (req.size < 2) throw std::runtime_error("size must be at least 2");
  if (req.target <= req.size) throw std::runtime_error("target must be greater than size");

  int max_val = req.target - 1;
  if (req.game_mode == "bounded_by_size_squared") {
    max_val = std::min(max_val, req.size * req.size);
  } else if (req.game_mode != "unbounded") {
    throw std::runtime_error("game_mode must be one of: unbounded, bounded_by_size_squared");
  }
  if (max_val < 1) throw std::runtime_error("no valid value range");

  State st;
  st.target = req.target;
  st.size = req.size;
  st.max_val = max_val;
  st.grid = req.known_grid;
  st.row_sums.assign(req.size, 0);
  st.col_sums.assign(req.size, 0);
  st.row_unknowns.assign(req.size, 0);
  st.col_unknowns.assign(req.size, 0);
  st.diag_sums.assign(2, 0);
  st.diag_unknowns.assign(2, 0);

  for (int r = 0; r < req.size; r++) {
    for (int c = 0; c < req.size; c++) {
      int v = st.grid[r][c];
      if (v == 0) {
        st.row_unknowns[r]++;
        st.col_unknowns[c]++;
        for (int d : diag_indexes(r, c, st.size)) st.diag_unknowns[d]++;
        st.unknowns.push_back({r, c});
      } else {
        if (v < 1 || v > max_val) throw std::runtime_error("known value out of range");
        if (st.used.count(v)) throw std::runtime_error("known_grid cannot contain duplicate values");
        st.used.insert(v);
        st.row_sums[r] += v;
        st.col_sums[c] += v;
        for (int d : diag_indexes(r, c, st.size)) st.diag_sums[d] += v;
      }
    }
  }

  return st;
}

bool solve_state(State &st, const std::string &solve_method) {
  bool propagation = solve_method == "mrv_backtracking_with_propagation" ||
                     solve_method == "mrv_backtracking_with_propagation_randomized";
  bool randomized = solve_method == "mrv_backtracking_randomized" ||
                    solve_method == "mrv_backtracking_with_propagation_randomized" ||
                    solve_method == "exhaustive_backtracking_randomized";
  bool exhaustive = solve_method == "exhaustive_backtracking" ||
                    solve_method == "exhaustive_backtracking_randomized";

  if (!propagation && !randomized && !exhaustive && solve_method != "mrv_backtracking") {
    throw std::runtime_error("unsupported solve_method");
  }

  return search(st, propagation, randomized, exhaustive);
}

std::string render_solution_json(const State &st) {
  std::string out = "{\"solution\":[";
  for (int r = 0; r < st.size; r++) {
    if (r > 0) out += ",";
    out += "[";
    for (int c = 0; c < st.size; c++) {
      if (c > 0) out += ",";
      out += std::to_string(st.grid[r][c]);
    }
    out += "]";
  }
  out += "]}";
  return out;
}

}  // namespace msolver
