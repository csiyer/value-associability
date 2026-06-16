library(tidyverse) 

## Setup for exp2
#loading data files
dm.image = read.csv("data/Exp1B.csv")

#select choice trials and preprocess data
choice = dm.image %>% filter(ttype == 'choice_task') |>
  group_by(ID) |>
  mutate(
    trial_num = row_number()
  )
choice = choice %>% filter(rt != "null") %>%
  mutate(
    delta.mem = as.numeric(mem_right) - as.numeric(mem_left),
    delta.value = as.numeric(value_right) - as.numeric(value_left),
    rt = as.numeric(rt),
    choseright = case_when(key_press == 75 ~ 1, key_press == 74 ~ 0),
    abs.mem = abs(delta.mem))

choice = choice %>% filter(rt >= 300)

#select rating trials to get subjective values of images from each participant
rating = dm.image %>% filter(ttype == 'rating_task') %>% 
  dplyr::group_by(ID) %>% mutate(z = scale(as.numeric(response)))
## z-score values for each subject
#calculate z scores within each ID
rating.merge = rating[c('ID', 'z', 'image')]
rating.merge.l = rating.merge %>% dplyr::rename(stim_left = image)
rating.merge.r = rating.merge %>% dplyr::rename(stim_right = image)

#merge columns based on ID and stimuli names
choice.z = merge(rating.merge.l, choice, by = c('ID', 'stim_left')) %>%
  dplyr::rename(z.value.l = z)
choice.z = merge(rating.merge.r, choice.z, by = c('ID', 'stim_right')) %>% 
  dplyr::rename(z.value.r = z)
choice.z = choice.z %>% mutate(z.delta.value = z.value.r - z.value.l)
choice.z = choice.z %>% mutate(abs.delta.v.z = abs(z.delta.value))

choice.z <- choice.z |> 
  mutate(
    mem_right = as.numeric(mem_right),
    mem_left = as.numeric(mem_left),
    SumMem = mem_right + mem_left,
    log_rt = log(rt),
    z.delta.value = z.delta.value[,1],
    z.value.r = z.value.r[,1],
    z.value.l = z.value.l[,1],
    abs.delta.v.z = abs.delta.v.z[,1],
    SumValue = z.value.r + z.value.l,
    delta.mem.v = case_when(delta.value > 0 ~ delta.mem, 
                   delta.value < 0 ~ -delta.mem,
                   delta.value == 0 ~ abs.mem),
    z.value.chosen = if_else(choseright == 1, z.value.r, z.value.l),
    z.value.unchosen = if_else(choseright == 1, z.value.l, z.value.r),
    mem_chosen = if_else(choseright == 1, mem_right, mem_left),
    mem_unchosen = if_else(choseright == 1, mem_left, mem_right),
    delta.v.z.chosen = z.value.chosen - z.value.unchosen,
    delta.mem.chosen = mem_chosen - mem_unchosen,
    consistent = if_else(sign(delta.v.z.chosen) == 1, TRUE, FALSE)
  )

## filter data into trials that delta value close to 0
#split trials into high/low delta mem based on within-subject median
# trials = 2939
choice.z = choice.z %>% 
  arrange(ID, abs.delta.v.z) %>% 
  group_by(ID) %>% 
  dplyr::mutate(rank.v = 1:n()) %>%
  dplyr::mutate(median.v = median(rank.v)) %>%
  ungroup()

choice.z <- choice.z |> 
  mutate(
    dv_type = if_else(rank.v <= median.v, "low", "high"),
    dv_type_c = if_else(rank.v <= median.v, -1, 1),
    dv_bin = if_else(rank.v <= median.v, 0, sign(z.delta.value)),
    delta.mem.v.alt = if_else(rank.v <= median.v, abs.mem, delta.mem.v)
  )

choice.low.v = choice.z %>% filter(rank.v <= median.v)
choice.high.v <- choice.z |> filter(rank.v > median.v)
