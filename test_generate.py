from datetime import date

from generate import key_value, uptime

assert uptime(date(2018, 11, 17), date(2026, 11, 11)) == "7 years, 11 months, 25 days"
assert uptime(date(2020, 1, 31), date(2020, 3, 1)) == "0 years, 1 month, 1 day"
assert uptime(date(2020, 1, 31), date(2020, 2, 28)) == "0 years, 0 months, 28 days"

assert "C&lt;&gt;&amp;" in key_value("Lang", "C<>&")

print("ok")
