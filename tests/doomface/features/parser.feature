Feature: Parse Doom STF status-bar face filenames
  As the tokenless orchestrator
  I want every standard 1993 Doom STF face name to parse deterministically
  So that the pipeline never stalls on a valid WAD asset

  Scenario Outline: Straight-ahead faces parse for every health tier and blink frame
    When I parse the filename "STFST<tier><frame>.png"
    Then the expression is "ST"
    And the health tier is <tier>
    And the gaze direction is "CENTER"

    Examples:
      | tier | frame |
      | 0    | 0     |
      | 0    | 1     |
      | 0    | 2     |
      | 1    | 0     |
      | 1    | 1     |
      | 1    | 2     |
      | 2    | 0     |
      | 2    | 1     |
      | 2    | 2     |
      | 3    | 0     |
      | 3    | 1     |
      | 3    | 2     |
      | 4    | 0     |
      | 4    | 1     |
      | 4    | 2     |

  Scenario Outline: Turn-right faces parse for every health tier
    When I parse the filename "STFTR<tier>0.png"
    Then the expression is "ST"
    And the health tier is <tier>
    And the gaze direction is "RIGHT"

    Examples:
      | tier |
      | 0    |
      | 1    |
      | 2    |
      | 3    |
      | 4    |

  Scenario Outline: Turn-left faces parse for every health tier
    When I parse the filename "STFTL<tier>0.png"
    Then the expression is "ST"
    And the health tier is <tier>
    And the gaze direction is "LEFT"

    Examples:
      | tier |
      | 0    |
      | 1    |
      | 2    |
      | 3    |
      | 4    |

  Scenario Outline: Ouch faces parse for every health tier
    When I parse the filename "STFOUCH<tier>.png"
    Then the expression is "OUCH"
    And the health tier is <tier>
    And the gaze direction is "CENTER"

    Examples:
      | tier |
      | 0    |
      | 1    |
      | 2    |
      | 3    |
      | 4    |

  Scenario Outline: Evil grin faces parse for every health tier
    When I parse the filename "STFEVL<tier>.png"
    Then the expression is "EVL"
    And the health tier is <tier>
    And the gaze direction is "CENTER"

    Examples:
      | tier |
      | 0    |
      | 1    |
      | 2    |
      | 3    |
      | 4    |

  Scenario Outline: Kill (berserk rampage) faces parse for every health tier
    When I parse the filename "STFKILL<tier>.png"
    Then the expression is "KILL"
    And the health tier is <tier>
    And the gaze direction is "CENTER"

    Examples:
      | tier |
      | 0    |
      | 1    |
      | 2    |
      | 3    |
      | 4    |

  Scenario: God-mode face parses as a health-tier-independent special
    When I parse the filename "STFGOD0.png"
    Then the expression is "GOD"
    And the health tier is 0
    And the gaze direction is "CENTER"

  Scenario: Dead face parses as a health-tier-independent special
    When I parse the filename "STFDEAD0.png"
    Then the expression is "DEAD"
    And the health tier is 0
    And the gaze direction is "CENTER"

  Scenario: Parsing is case-insensitive on the stem
    When I parse the filename "stftr20.png"
    Then the expression is "ST"
    And the health tier is 2
    And the gaze direction is "RIGHT"

  Scenario: A bare lump name with no extension parses the same as a PNG
    When I parse the filename "STFOUCH3"
    Then the expression is "OUCH"
    And the health tier is 3
    And the gaze direction is "CENTER"

  Scenario Outline: Names outside the STF convention are rejected
    When I parse the filename "<filename>"
    Then parsing raises an invalid name error

    Examples:
      | filename      |
      | TROOA1.png    |
      | STFST5.png    |
      | STFST55.png   |
      | STFTR05.png   |
      | STFOUCH5.png  |
      | STFEVL.png    |
      | STFKILL02.png |
      | STFGOD1.png   |
      | STFDEAD1.png  |
      | not_a_doom_sprite.png |
