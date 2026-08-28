"""Single executable source for site-graph-v0 product decision constants."""

from fractions import Fraction


MUSEUMS = ("met", "brooklyn", "harvard")
PAIRS = (("met", "brooklyn"), ("met", "harvard"), ("brooklyn", "harvard"))
OPPORTUNITY_MUSEUM_PROTECTION = 10
OPPORTUNITY_TOTAL_SIGNATURES = 50
MINIMUM_AFFECTED_FRACTION = Fraction(1, 10)
MINIMUM_GAINED_IDENTITIES = 2
AMBIGUITY_MAXIMUM_INCREASE = Fraction(5, 1000)
CONCENTRATION_MAXIMUM_INCREASE = Fraction(5, 100)
REVIEWS_PER_CREDITED_DECISION = 2
