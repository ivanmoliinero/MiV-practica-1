"""
Voting Eligible Population (VEP) statistics per US state for the 2024 General Election.

Source: University of Florida Election Lab (directed by Dr. Michael McDonald, formerly US Elections Project)
Dataset: Turnout_2024G_v0.4.csv (May 2026 release)
Official Portal: https://election.lab.ufl.edu/2024-general-election-turnout/
Direct CSV URL: https://election.lab.ufl.edu/data-downloads/turnoutdata/Turnout_2024G_v0.4.csv

VEP represents the total Voting-Age Population (18+) minus ineligible non-citizens and
disenfranchised felons according to state law.
"""

from typing import Dict

# Official 2024 General Election Voting-Eligible Population (VEP) by state
STATE_VEP: Dict[str, int] = {
    "Alabama": 3_867_406,
    "Alaska": 536_581,
    "Arizona": 5_366_526,
    "Arkansas": 2_201_764,
    "California": 25_922_868,
    "Colorado": 4_415_631,
    "Connecticut": 2_670_153,
    "Delaware": 776_224,
    "Florida": 16_327_632,
    "Georgia": 7_793_977,
    "Hawaii": 1_038_968,
    "Idaho": 1_429_619,
    "Illinois": 8_982_526,
    "Indiana": 5_041_013,
    "Iowa": 2_359_332,
    "Kansas": 2_122_704,
    "Kentucky": 3_327_188,
    "Louisiana": 3_305_398,
    "Maine": 1_130_059,
    "Maryland": 4_411_216,
    "Massachusetts": 5_132_767,
    "Michigan": 7_624_237,
    "Minnesota": 4_277_436,
    "Mississippi": 2_164_463,
    "Missouri": 4_642_204,
    "Montana": 896_053,
    "Nebraska": 1_406_843,
    "Nevada": 2_249_102,
    "New Hampshire": 1_127_497,
    "New Jersey": 6_401_643,
    "New Mexico": 1_554_606,
    "New York": 13_853_326,
    "North Carolina": 8_102_246,
    "North Dakota": 582_216,
    "Ohio": 8_947_502,
    "Oklahoma": 2_945_902,
    "Oregon": 3_211_515,
    "Pennsylvania": 9_903_829,
    "Rhode Island": 826_559,
    "South Carolina": 4_121_955,
    "South Dakota": 676_581,
    "Tennessee": 5_317_723,
    "Texas": 20_059_077,
    "Utah": 2_357_958,
    "Vermont": 527_067,
    "Virginia": 6_350_428,
    "Washington": 5_640_909,
    "West Virginia": 1_387_010,
    "Wisconsin": 4_483_698,
    "Wyoming": 442_780,
}
