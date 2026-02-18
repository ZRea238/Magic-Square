#include <iostream>
#include <sstream>
#include <stdexcept>

#include "json_parser.hpp"
#include "solver.hpp"

int main() {
  try {
    std::stringstream buffer;
    buffer << std::cin.rdbuf();
    std::string input = buffer.str();

    msolver::JsonParser parser(input);
    msolver::JsonValue root = parser.parse();
    msolver::Request req = msolver::parse_request(root);
    msolver::State st = msolver::build_state(req);

    if (!msolver::solve_state(st, req.solve_method)) {
      throw std::runtime_error("No valid solution for the provided target and known grid");
    }

    std::cout << msolver::render_solution_json(st) << std::endl;
  } catch (const std::exception &ex) {
    std::cerr << ex.what() << std::endl;
    return 1;
  }

  return 0;
}
