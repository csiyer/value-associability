library(tidyverse)
library(lme4)
library(broom.mixed)

data <- read_csv("task2UncertaintyData.csv")

# https://codeocean.com/capsule/2024716/tree/v1/fit_task2_regs.R
# data = data[!is.na(data$old_value),]
# data$old_value_centered = ( data[,"old_value"] - mean(data[,"old_value"]) )
# data$true_deck_centered = ( data[,"true_deck_value"] - mean(data[,"true_deck_value"]) )

# support_functions.py, recode_old_deck
# #.5=orange old;0=both new;-.5=blue old
data <- data |>
  filter_out(is.na(old_value)) |>
  mutate(
    old_value_centered = old_value - mean(old_value),
    true_deck_centered = true_deck_value - mean(true_deck_value),
    old_object = if_else(old_deck == .5, orange_object, blue_object)
  )

m1 <- glmer(old_chosen ~ old_value_centered + true_deck_centered + 
             (old_value_centered + true_deck_centered | sub_factor),
           data = data, family = binomial(link = "logit"))
saveRDS(m1, "m1.RDS")

m2 <- glmer(old_chosen ~ old_value_centered + true_deck_centered + 
             (old_value_centered + true_deck_centered | sub_factor) +
             (old_value_centered || old_object),
           data = data, family = binomial(link = "logit"))
saveRDS(m2, "m2.RDS")

m3 <- glmer(old_chosen ~ old_value_centered + true_deck_centered + 
             (old_value_centered + true_deck_centered | sub_factor) +
             (old_value_centered | old_object),
           data = data, family = binomial(link = "logit"))
saveRDS(m3, "m3.RDS")