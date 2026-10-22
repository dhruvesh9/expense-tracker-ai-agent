"""Services: business rules. They know nothing about HTTP; they receive plain
arguments, call repositories, own the transaction (commit) and raise AppErrors."""
