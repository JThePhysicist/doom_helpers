Feature: Parsing Doom STF status-bar face filenames
  As the tokenless sprite pipeline
  I want to deterministically parse every real 1993 STF face filename
  So that later phases always get a valid target FaceState

  Scenario Outline: Main health/gaze grid faces parse correctly
    When I parse the STF filename "<filename>"
    Then the expression should be "ST"
    And the health tier should be <tier>
    And the gaze direction should be <gaze>

    Examples:
      | filename    | tier | gaze |
      | STFST00.png | 0    | 0    |
      | STFST01.png | 0    | 1    |
      | STFST02.png | 0    | 2    |
      | STFST03.png | 0    | 1    |
      | STFST04.png | 0    | 2    |
      | STFST10.png | 1    | 0    |
      | STFST14.png | 1    | 2    |
      | STFST20.png | 2    | 0    |
      | STFST31.png | 3    | 1    |
      | STFST44.png | 4    | 2    |

  Scenario Outline: Turning faces parse correctly
    When I parse the STF filename "<filename>"
    Then the expression should be "<expression>"
    And the health tier should be 0
    And the gaze direction should be <gaze>

    Examples:
      | filename    | expression | gaze |
      | STFTR00.png | TR         | 1    |
      | STFTL00.png | TL         | 2    |

  Scenario Outline: Pain, evil grin, and berserk faces parse correctly for every health tier
    When I parse the STF filename "<filename>"
    Then the expression should be "<expression>"
    And the health tier should be <tier>
    And the gaze direction should be 0

    Examples:
      | filename      | expression | tier |
      | STFOUCH0.png  | OUCH       | 0    |
      | STFOUCH1.png  | OUCH       | 1    |
      | STFOUCH2.png  | OUCH       | 2    |
      | STFOUCH3.png  | OUCH       | 3    |
      | STFOUCH4.png  | OUCH       | 4    |
      | STFEVL0.png   | EVL        | 0    |
      | STFEVL1.png   | EVL        | 1    |
      | STFEVL2.png   | EVL        | 2    |
      | STFEVL3.png   | EVL        | 3    |
      | STFEVL4.png   | EVL        | 4    |
      | STFKILL0.png  | KILL       | 0    |
      | STFKILL1.png  | KILL       | 1    |
      | STFKILL2.png  | KILL       | 2    |
      | STFKILL3.png  | KILL       | 3    |
      | STFKILL4.png  | KILL       | 4    |

  Scenario Outline: Single-frame special faces parse correctly
    When I parse the STF filename "<filename>"
    Then the expression should be "<expression>"
    And the health tier should be 0
    And the gaze direction should be 0

    Examples:
      | filename    | expression |
      | STFGOD0.png | GOD        |
      | STFDEAD0.png | DEAD      |

  Scenario Outline: Filenames outside the STF convention are rejected
    When I try to parse the invalid STF filename "<filename>"
    Then parsing should raise a ValueError

    Examples:
      | filename        |
      | TROOA1.png       |
      | STFST55.png       |
      | STFOUCH5.png       |
      | not_a_sprite.png    |
      | STF.png              |
