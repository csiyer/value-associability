library(tidyverse)
library(lme4)
library(lmerTest)
library(broom.mixed)
library(psych)

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
    enc_time_point = lag(trial_id),
    delay = trial_id - enc_time_point
  ) |> group_by(subj_id) |>
  mutate(
    lag_delay = lag(delay),
    lag_enc = delay - lag_delay - 1,
    lag_choice_optimal = lag(choice_optimal)
  ) |>
  ungroup()

model_df <- train_data |> 
  filter(!(subj_id %in% bad_subs), trial_type_str == "old-new") |>
  mutate(
    old_value = if_else(is_old_l == 1, value_l, value_r),
    old_optimal = old_value == 100,
    old_optimal_c = if_else(old_optimal, .5, -.5),
    choice_optimal_c = if_else(choice_optimal, .5, -.5)
  )


# Delay effect ------------------------------------------------------------

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

sub_delay_df <- model_df |>
  filter(delay >= 9, delay <= 18) |>
  group_by(subj_id, delay, choice_optimal) |>
  summarize(
    rt = mean(item_trial.rt, na.rm = TRUE)
  )
sub_delay_df |>
  ggplot(aes(x = delay, y = rt, color = choice_optimal, group = choice_optimal)) +
  stat_summary() +
  stat_summary(geom = "line") +
  labs(x = "Delay", y = "P(Optimal Choice)") +
  theme_classic()
sub_value_delay_df <- model_df |>
  filter(delay >= 9, delay <= 18) |>
  group_by(subj_id, delay, old_value, choice_optimal) |>
  summarize(
    rt = mean(item_trial.rt, na.rm = TRUE)
  )
sub_value_delay_df |>
  ggplot(aes(x = delay, y = rt, color = factor(old_value), linetype = choice_optimal, group = interaction(old_value, choice_optimal))) +
  stat_summary() +
  stat_summary(geom = "line") +
  labs(x = "Delay", y = "P(Optimal Choice)", color = "Old Item Value") +
  theme_classic()


# Lag-CRP (for fun) -------------------------------------------------------

sub_lag_enc_df <- model_df |>
  filter(delay >= 9, delay <= 18, lag_delay >= 9, lag_delay <= 18, lag_enc >= -3, lag_enc <= 3, lag_choice_optimal) |>
  group_by(subj_id, lag_enc) |>
  summarize(
    p_choice_optimal = mean(choice_optimal, na.rm = TRUE)
  )
sub_lag_enc_df |>
  ggplot(aes(x = lag_enc, y = p_choice_optimal)) +
  stat_summary() +
  stat_summary(geom = "line") +
  theme_classic()

sub_lag_enc_df <- model_df |>
  filter(delay >= 9, delay <= 18, lag_delay >= 9, lag_delay <= 18, lag_enc >= -3, lag_enc <= 3, lag_choice_optimal) |>
  group_by(subj_id, lag_enc, choice_optimal) |>
  summarize(
    rt = mean(item_trial.rt, na.rm = TRUE)
  )
sub_lag_enc_df |>
  ggplot(aes(x = lag_enc, y = rt, color = choice_optimal)) +
  stat_summary() +
  stat_summary(geom = "line") +
  theme_classic()


# Choice models -----------------------------------------------------------

m0 <- glmer(choice_optimal ~ 1 + (1 | subj_id), family = binomial, data = model_df)
m1 <- glmer(choice_optimal ~ 1 + (1 | subj_id) + (1 | old_item), family = binomial, data = model_df)
anova(m0, m1)

m0 <- glmer(chosen_is_old ~ old_optimal_c + (old_optimal_c | subj_id), family = binomial, data = model_df)
m1 <- glmer(chosen_is_old ~ old_optimal_c + (old_optimal_c | subj_id) + (1 | old_item), family = binomial, data = model_df)
m2 <- glmer(chosen_is_old ~ old_optimal_c + (old_optimal_c | subj_id) + (old_optimal_c || old_item), family = binomial, data = model_df)
m3 <- glmer(chosen_is_old ~ old_optimal_c + (old_optimal_c | subj_id) + (old_optimal_c | old_item), family = binomial, data = model_df)
anova(m0, m1, m2, m3)
anova(m0, m1)

# RT models ---------------------------------------------------------------

m0_rt <- lmer(item_trial.rt ~ choice_optimal_c * old_optimal_c + (choice_optimal_c * old_optimal_c | subj_id), data = model_df)
m0_rt_ns1 <- lmer(item_trial.rt ~ choice_optimal_c * old_optimal_c + (choice_optimal_c * old_optimal_c || subj_id), data = model_df)
m1_rt_ns1 <- lmer(item_trial.rt ~ choice_optimal_c * old_optimal_c + (choice_optimal_c * old_optimal_c || subj_id) + (choice_optimal_c * old_optimal_c || old_item), data = model_df)
m1_rt_ns2 <- lmer(item_trial.rt ~ choice_optimal_c * old_optimal_c + (choice_optimal_c * old_optimal_c || subj_id) + (choice_optimal_c + old_optimal_c || old_item), data = model_df)
m1_rt_ns3 <- lmer(item_trial.rt ~ choice_optimal_c * old_optimal_c + (choice_optimal_c * old_optimal_c || subj_id) + (choice_optimal_c || old_item), data = model_df)
anova(m0_rt_ns1, m1_rt_ns3)

m0a_rt_ns1 <- lmer(item_trial.rt ~ choice_optimal_c * old_optimal_c + (choice_optimal_c + choice_optimal_c:old_optimal_c | subj_id) + (0 + old_optimal_c | subj_id), data = model_df)
m1a_rt_ns1 <- lmer(item_trial.rt ~ choice_optimal_c * old_optimal_c + (choice_optimal_c + choice_optimal_c:old_optimal_c | subj_id) + (0 + old_optimal_c | subj_id) + (choice_optimal_c * old_optimal_c || old_item), data = model_df)
m1a_rt_ns2 <- lmer(item_trial.rt ~ choice_optimal_c * old_optimal_c + (choice_optimal_c + choice_optimal_c:old_optimal_c | subj_id) + (0 + old_optimal_c | subj_id) + (choice_optimal_c + choice_optimal_c:old_optimal_c || old_item), data = model_df)
m1a_rt_ns3 <- lmer(item_trial.rt ~ choice_optimal_c * old_optimal_c + (choice_optimal_c + choice_optimal_c:old_optimal_c | subj_id) + (0 + old_optimal_c | subj_id) + (choice_optimal_c || old_item), data = model_df)
m1a_rt_ns4 <- lmer(item_trial.rt ~ choice_optimal_c * old_optimal_c + (choice_optimal_c + choice_optimal_c:old_optimal_c | subj_id) + (0 + old_optimal_c | subj_id) + (choice_optimal_c | old_item), data = model_df)
anova(m0a_rt_ns1, m1a_rt_ns3)

m1a_rt_ns3_res <- m1a_rt_ns3 |>
  tidy(effects = "ran_vals")

m1a_rt_ns3_res |> filter(group == "old_item", term == "choice_optimal_c") |> arrange(estimate)

resmem_scores <- read.csv('resmem_scores.csv')

resmem_model_df <- model_df |> 
  left_join(resmem_scores, by = join_by(old_item == image_path)) |>
  mutate(
    memscore_z = scale(memscore)
  )

m2 <- glmer(chosen_is_old ~ old_optimal_c * memscore_z + 
              (old_optimal_c | subj_id) + (old_optimal_c | old_item), 
            family = binomial, data = resmem_model_df)
summary(m2)

m2a <- glmer(chosen_is_old ~ old_optimal_c + 
              (old_optimal_c | subj_id), 
            family = binomial, data = model_df)
m2b <- glmer(chosen_is_old ~ old_optimal_c + 
              (old_optimal_c | subj_id) + (1 | old_item), 
            family = binomial, data = model_df)
m2c <- glmer(chosen_is_old ~ old_optimal_c + 
              (old_optimal_c | subj_id) + (old_optimal_c || old_item), 
            family = binomial, data = model_df)
m2d <- glmer(chosen_is_old ~ old_optimal_c + 
              (old_optimal_c | subj_id) + (old_optimal_c | old_item), 
            family = binomial, data = model_df)
m2e <- glmer(chosen_is_old ~ old_optimal_c + 
               (old_optimal_c | subj_id) + (0 + old_optimal_c | old_item), 
             family = binomial, data = model_df)
anova(m2a, m2b, m2c, m2d)
anova(m2a, m2e)

sub_value_df <- model_df |>
  filter(delay >= 9, delay <= 18) |>
  group_by(subj_id, old_value) |>
  summarize(
    p_chosen_is_old = mean(chosen_is_old, na.rm = TRUE)
  )
sub_value_df |>
  ggplot(aes(x = old_value, y = p_chosen_is_old)) +
  stat_summary() +
  labs(x = "Old Value", y = "P(Old)") +
  theme_classic()
