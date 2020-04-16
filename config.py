supported_methods = ["GET", "POST"]
# actions
PASS = "PASS"
BLOCK = "BLOCK"

# default action in case request doesn't match any entry
default_action = PASS

# [(HOST, METHOD, PATH), ACTION]
policy = [ [("www.google.com", "GET", ""), PASS],
           [("www.malicious.com", "GET", "malicious"), BLOCK],
           [("www.google.co.il", "POST", "bad"), BLOCK]
         ]
