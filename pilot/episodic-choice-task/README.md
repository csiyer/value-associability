# Episodic Choice Task

This script replicates the basic task from [Duncan and Shohamy 2016](http://duncanlab.org/wp-content/uploads/2018/04/Duncan_2016.pdf), without the contextual cues.

Participants choose between cards, with random values. Sometimes a card reappears, and participants can use their memory to remember its value and decide whether to pick it.

Cards use the same images sampled from the THINGS dataset and evaluated for associability in the `associability-task`.


## Sequence constraints
We pre-compute sequences for our tasks using MILP to satisfy matching of different experimental conditions. They are listed below. 

### Main task version (Duncan & Shohamy 2016 version)
- 312 trials, 50% old and 50% new
- All trials have both cards same memorability bin (high, medium, low)
- New trials have 2 new images
- Old trials have 1 old (previously chosen) and 1 new
    - 156 old trials, 52 in each of 3 mem bins
    - 26 $0, and 26 $1
    - the value of the new card is random but balanced across bins
    - the side of the old card is balanced l/r
- Delays between 7 and 15
	- The 3 memorability bins should have exactly the same delay counts
- No run of the same memorability longer than 3
- No run of the same trial type longer than 8
=== NO LONGER === Each set of 3 trials should have one high-mem, one low-mem, and one mid-men trial (triplet).
Ordering of the trial types feels somewhat random to participants


### Mixed-memorability
- 156 new trials, 78 old trials
- 78 new trials are high-mem (both new images), 78 are low-mem
- 39 of each category are $1 and 39 are $0
- Old trials are old/old, always different memorability
- 4 types of old trials: 
    - “even” both $1, or both $0
        - match delays between these two conditions, and between the high mem and low mem images
        - 40 even trials, 20 of each type
    - “uneven” one is $1, one is $0
        - high is $1/low$0, or high$0, low$1
        - 38 uneven trials, 19 of each type
        -- match delays between high value and low value, high mem and low mem item
- Delays always 7-15
- Which has a longer delay (left vs. right, on uneven trials $1 vs $0 is balanced)
- The two different memorability bins share the exact same delay distributions
- No run of the same memorability longer than 3
- No run of the same trial type longer than 8
Ordering of the trial types feels somewhat random to participants

### Matched-memorability
- 156 new trials, 78 old trials
- 78 new trials are high-mem (both new images), 78 are low-mem
- 39 of each category are $1 and 39 are $0
- Old trials are old/old, always same memorability
- 39 high memorability, 39 low memorability
- Always one $1, and one $0
- Delays always 7-15
- Which has a longer delay (the $1 or $0, and the left vs. right is balanced)
- The two different memorability bins share the exact same delay distributions
- No run of the same memorability longer than 3
- No run of the same trial type longer than 8
Ordering of the trial types feels somewhat random to participants