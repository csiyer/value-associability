library(tidyverse)

source("memorability_analysis.R")

#load data for Exp2A (representativeness task)
# dat = read.csv("data/Exp2A.csv")
# #calculate average z-scored rep data for each image/word pairs
# rep = dat %>% filter(ttype == "rep_rating")
# rep = rep %>% dplyr::group_by(run_id) %>% dplyr::mutate(z.score = scale(as.numeric(response)))
# rep.mean = rep %>% dplyr::group_by(word) %>% 
#   dplyr::summarize(rep = mean(as.numeric(response)), rep.z = mean(z.score), n = n()) %>% 
#   select(-n)
# mem = merge(rep.mean, mem, by.x = "word", by.y = "food.item")

#Load memorability data
dat.w = read.csv("data/Exp2B.csv")

#apply function for calculating memorability scores
img.values.w = calculate_mem(dat.w) %>% dplyr::rename(word.mem = Memorability)

mem <- img.values.w |> rename(word = "image")

#summarize data and combine it with image/word indexes
# mem = merge(img.values.w, mem, by.x = "image", by.y = "word")

## Setup for exp2C
#loading data files
dm.word = read.csv("data/Exp2C.csv")

#select choice trials and preprocess data
choice.w = dm.word %>% filter(ttype == 'choice_task')
choice.w = choice.w %>% filter(rt != "null", rt != 0) %>% 
  mutate(rt = as.numeric(rt),
         delta.value = as.numeric(value_right) - as.numeric(value_left),
         choseright = case_when(response == 'k' ~ 1, response =='j' ~ 0)) %>%
  dplyr::group_by(ID) %>% dplyr::mutate(z.delta.value = scale(delta.value)) %>%
  mutate(abs.delta.v.z = abs(z.delta.value),
         chosehigh.value = case_when(choseright == 1 & delta.value >=0 ~ 1, choseright == 0 & delta.value <0 ~ 1, choseright == 1 & delta.value <0 ~ 0,choseright == 0 & delta.value >=0 ~ 0 ))

#exclude trails that have RT lower than 300
choice.w = choice.w %>% filter(rt >= 300)

#select rating trials to get subjective values of images from each participant
rating.w = dm.word %>% filter(ttype == 'rating_task') %>% 
  dplyr::group_by(ID) %>% mutate(z = scale(as.numeric(response)))

#merge word memorability based on words and stimuli position
word.mem = select(mem, word.mem, word)
choice.test = merge(word.mem, choice.w, by.x = 'word', by.y = 'stim_left') %>%
  dplyr::rename(stim_left = word, mem.l = word.mem)
choice.test = merge(word.mem, choice.test, by.x = 'word', by.y = 'stim_right') %>%
  dplyr::rename(stim_right = word, mem.r = word.mem)

choice.test = choice.test %>% mutate(
  delta.mem = as.numeric(mem.r) - as.numeric(mem.l)) %>% 
  mutate(abs.mem = abs(delta.mem)) %>% 
  mutate(chosehigh.mem = case_when(
    choseright == 1 & delta.mem >=0 ~ 1, 
    choseright == 0 & delta.mem <0 ~ 1, 
    choseright == 1 & delta.mem <0 ~ 0,
    choseright == 0 & delta.mem >=0 ~ 0 ))

rating.w_sel <- rating.w |> 
  select(ID, word, z)
choice.test <- choice.test |> 
  left_join(rating.w_sel, by = join_by("ID", "stim_left" == "word")) |>
  left_join(rating.w_sel, by = join_by("ID", "stim_right" == "word"), suffix = c(".value.l", ".value.r"))

choice.test <- choice.test |> 
  mutate(
    SumMem = mem.l + mem.r,
    log_rt = log(rt),
    ID_fct = factor(ID),
    z.delta.value = z.delta.value[,1],
    z.value.r = z.value.r[,1],
    z.value.l = z.value.l[,1],
    abs.delta.v.z = abs.delta.v.z[,1],
    SumValue = z.value.r + z.value.l,
    abs.delta.mem = abs(delta.mem),
    delta.mem.v = case_when(delta.value > 0 ~ delta.mem, 
                            delta.value < 0 ~ -delta.mem,
                            delta.value == 0 ~ abs.delta.mem),
    z.value.chosen = if_else(choseright == 1, z.value.r, z.value.l),
    z.value.unchosen = if_else(choseright == 1, z.value.l, z.value.r),
    mem_chosen = if_else(choseright == 1, mem.r, mem.l),
    mem_unchosen = if_else(choseright == 1, mem.l, mem.r),
    delta.v.z.chosen = z.value.chosen - z.value.unchosen,
    delta.mem.chosen = mem_chosen - mem_unchosen,
    consistent = if_else(sign(delta.v.z.chosen) == 1, TRUE, FALSE)
  )

## filter data into trials that delta value close to 0
#split trials into high/low delta mem based on within-subject median
choice.test = choice.test %>% 
  arrange(ID, abs.delta.v.z) %>% 
  group_by(ID) %>% 
  dplyr::mutate(rank.v = 1:n()) %>% 
  dplyr::mutate(median.v = median(rank.v)) %>%
  ungroup()

choice.test <- choice.test |> 
  mutate(
    dv_type = if_else(rank.v <= median.v, "low", "high"),
    dv_type_c = if_else(rank.v <= median.v, -1, 1),
    dv_bin = if_else(rank.v <= median.v, 0, sign(z.delta.value)),
    delta.mem.v.alt = if_else(rank.v <= median.v, abs.delta.mem, delta.mem.v)
  )

choice.low.v.w = choice.test %>% filter(rank.v <= median.v)
choice.high.v.w <- choice.test |> filter(rank.v > median.v)
