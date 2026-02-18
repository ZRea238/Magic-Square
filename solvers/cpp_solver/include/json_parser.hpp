#ifndef MAGIC_SQUARE_JSON_PARSER_HPP
#define MAGIC_SQUARE_JSON_PARSER_HPP

#include <map>
#include <string>
#include <vector>

namespace msolver {

struct JsonValue {
  enum Type { Null, Number, String, Array, Object } type = Null;
  long long number = 0;
  std::string str;
  std::vector<JsonValue> array;
  std::map<std::string, JsonValue> object;
};

class JsonParser {
 public:
  explicit JsonParser(const std::string &s);
  JsonValue parse();

 private:
  const std::string &s_;
  size_t i_;

  void skip_ws();
  JsonValue parse_value();
  JsonValue parse_null();
  JsonValue parse_number();
  JsonValue parse_string();
  JsonValue parse_array();
  JsonValue parse_object();
};

}  // namespace msolver

#endif
