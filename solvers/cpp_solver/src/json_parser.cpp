#include "json_parser.hpp"

#include <stdexcept>

namespace msolver {

JsonParser::JsonParser(const std::string &s) : s_(s), i_(0) {}

JsonValue JsonParser::parse() {
  skip_ws();
  JsonValue v = parse_value();
  skip_ws();
  return v;
}

void JsonParser::skip_ws() {
  while (i_ < s_.size() && (s_[i_] == ' ' || s_[i_] == '\n' || s_[i_] == '\r' || s_[i_] == '\t')) i_++;
}

JsonValue JsonParser::parse_value() {
  skip_ws();
  if (i_ >= s_.size()) throw std::runtime_error("unexpected end of json");
  char c = s_[i_];
  if (c == 'n') return parse_null();
  if (c == '"') return parse_string();
  if (c == '[') return parse_array();
  if (c == '{') return parse_object();
  if (c == '-' || (c >= '0' && c <= '9')) return parse_number();
  throw std::runtime_error("invalid json token");
}

JsonValue JsonParser::parse_null() {
  if (s_.substr(i_, 4) != "null") throw std::runtime_error("invalid null");
  i_ += 4;
  JsonValue v;
  v.type = JsonValue::Null;
  return v;
}

JsonValue JsonParser::parse_number() {
  size_t start = i_;
  if (s_[i_] == '-') i_++;
  while (i_ < s_.size() && s_[i_] >= '0' && s_[i_] <= '9') i_++;
  JsonValue v;
  v.type = JsonValue::Number;
  v.number = std::stoll(s_.substr(start, i_ - start));
  return v;
}

JsonValue JsonParser::parse_string() {
  if (s_[i_] != '"') throw std::runtime_error("expected string");
  i_++;
  std::string out;
  while (i_ < s_.size()) {
    char c = s_[i_++];
    if (c == '"') break;
    if (c == '\\') {
      if (i_ >= s_.size()) throw std::runtime_error("invalid escape");
      char e = s_[i_++];
      if (e == '"' || e == '\\' || e == '/') out.push_back(e);
      else if (e == 'b') out.push_back('\b');
      else if (e == 'f') out.push_back('\f');
      else if (e == 'n') out.push_back('\n');
      else if (e == 'r') out.push_back('\r');
      else if (e == 't') out.push_back('\t');
      else throw std::runtime_error("unsupported escape");
    } else {
      out.push_back(c);
    }
  }
  JsonValue v;
  v.type = JsonValue::String;
  v.str = out;
  return v;
}

JsonValue JsonParser::parse_array() {
  if (s_[i_] != '[') throw std::runtime_error("expected array");
  i_++;
  JsonValue v;
  v.type = JsonValue::Array;
  skip_ws();
  if (i_ < s_.size() && s_[i_] == ']') {
    i_++;
    return v;
  }
  while (true) {
    v.array.push_back(parse_value());
    skip_ws();
    if (i_ >= s_.size()) throw std::runtime_error("unterminated array");
    if (s_[i_] == ']') {
      i_++;
      break;
    }
    if (s_[i_] != ',') throw std::runtime_error("expected comma in array");
    i_++;
  }
  return v;
}

JsonValue JsonParser::parse_object() {
  if (s_[i_] != '{') throw std::runtime_error("expected object");
  i_++;
  JsonValue v;
  v.type = JsonValue::Object;
  skip_ws();
  if (i_ < s_.size() && s_[i_] == '}') {
    i_++;
    return v;
  }
  while (true) {
    skip_ws();
    JsonValue k = parse_string();
    skip_ws();
    if (i_ >= s_.size() || s_[i_] != ':') throw std::runtime_error("expected colon");
    i_++;
    JsonValue val = parse_value();
    v.object[k.str] = val;
    skip_ws();
    if (i_ >= s_.size()) throw std::runtime_error("unterminated object");
    if (s_[i_] == '}') {
      i_++;
      break;
    }
    if (s_[i_] != ',') throw std::runtime_error("expected comma in object");
    i_++;
  }
  return v;
}

}  // namespace msolver
