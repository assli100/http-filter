supported_methods = ["GET", "POST"]
# actions
PASS = "PASS"
BLOCK = "BLOCK"

# default action in case request doesn't match any entry
default_action = PASS

# seconds to wait for the upstream server
upstream_timeout = 30

# [(HOST, METHOD, PATH), ACTION]
# Matching ignores case and the port. PATH matches that path and everything
# under it ("bad" matches "/bad" and "/bad/x"); "" matches every path.
# The first matching entry wins.
policy = [ [("www.google.com", "GET", ""), PASS],
           [("www.malicious.com", "GET", "malicious"), BLOCK],
           [("www.google.co.il", "POST", "bad"), BLOCK]
         ]
