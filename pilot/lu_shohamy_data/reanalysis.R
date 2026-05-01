library(tidyverse)
library(lme4)
library(lmerTest)

# data from pilot analysis https://osf.io/4ukgw/files/osfstorage?view_only=f09e5d80eb79414381e3db8bb05e55e8
indep_df_proc <- read_csv("indep-df-proc.csv") |>
  rename(subj_id = "subj id") 

#from cleaned-compare-condition.py
n_train_trials_here <- 660
id_1st_test_trial <- 680
id_final_test_trial <- 800

train_data <- indep_df_proc |> 
  filter(trial_id < n_train_trials_here)

test_data <- indep_df_proc |> 
  filter(trial_id > id_1st_test_trial)

# Following Qu, use test data to detect bad subjects
sub_choice_optimal_test <- test_data |>
  filter(trial_type == 1) |>
  mutate(
    choice_optimal = reward == max(value_l, value_r)
  ) |>
  group_by(subj_id) |>
  summarize(choice_optimal = mean(choice_optimal, na.rm = TRUE))
# Q uses binomial test but .4 seems to be enough
bad_subs <- sub_choice_optimal_test |> 
  filter(choice_optimal < .4) |> 
  distinct(subj_id) |> pull()

#cleaned-process-pilot-data.py line 209 - 214
train_data <- train_data |>
  group_by(subj_id) |>
  mutate(
    choice_optimal = reward == max(value_l, value_r),
    trial_type_str = if_else(trial_type == 1, "old-new", "new-new"),
    old_item = case_when(
      trial_type == 0 ~ chosen_item, #useful for computing delay
      is_old_l == 1 ~ image_l,
      is_old_r == 1 ~ image_r
    )
  ) |>
  group_by(subj_id, old_item) |>
  mutate(
    old_trial_id = lag(trial_id),
    delay = trial_id - old_trial_id
  ) |> ungroup()

model_df <- train_data |> 
  filter(!(subj_id %in% bad_subs), trial_type_str == "old-new") |>
  mutate(
    old_value = if_else(is_old_l == 1, value_l, value_r),
    old_optimal = old_value == 100,
    old_optimal_c = if_else(old_optimal, .5, -.5)
  )

# delay effect
sub_delay_df <- model_df |>
  filter(delay >= 9, delay <= 18) |>
  group_by(subj_id, delay) |>
  summarize(
    p_choice_optimal = mean(choice_optimal, na.rm = TRUE)
  )
sub_delay_df |>
  ggplot(aes(x = delay, y = p_choice_optimal)) +
  stat_summary() +
  labs(x = "Delay", y = "P(Optimal Choice)") +
  theme_classic()
sub_value_delay_df <- model_df |>
  filter(delay >= 9, delay <= 18) |>
  group_by(subj_id, delay, old_value) |>
  summarize(
    p_choice_optimal = mean(choice_optimal, na.rm = TRUE)
  )
sub_value_delay_df |>
  ggplot(aes(x = delay, y = p_choice_optimal, color = factor(old_value), group = old_value)) +
  stat_summary() +
  stat_summary(geom = "line") +
  labs(x = "Delay", y = "P(Optimal Choice)", color = "Old Item Value") +
  theme_classic()

m0 <- glmer(choice_optimal ~ 1 + (1 | subj_id), family = binomial, data = model_df)
m1 <- glmer(choice_optimal ~ 1 + (1 | subj_id) + (1 | old_item), family = binomial, data = model_df)
anova(m0, m1)

m0 <- glmer(choice_optimal ~ old_optimal_c + (old_optimal_c | subj_id), family = binomial, data = model_df)
m1 <- glmer(choice_optimal ~ old_optimal_c + (old_optimal_c | subj_id) + (old_optimal_c | old_item), family = binomial, data = model_df)
anova(m0, m1)
