library(tidyverse)
library(lme4)

episodic_choice_data <- read_csv("~/Documents/GitHub/value-associability/episodic-choice-task/data/episodic_choice_data.csv")

FAILED_ATTENTION_PIDS <- episodic_choice_data |> 
  filter(is_attention_check) |> 
  group_by(participant_id) |> 
  summarize(correct = mean(correct)) |>
  filter(correct < .8)

old_trials_df <- episodic_choice_data |>
  filter(participant_id %notin% FAILED_ATTENTION_PIDS, old_trial == 1)

binom_test_df <- old_trials_df |>
  filter_out(is.na(optimal_old_choice)) |>
  group_by(participant_id) |>
  summarize(
    n_optimal_old_choices = sum(optimal_old_choice),
    n_responses = n()
  ) |>
  rowwise() |>
  mutate(
    p.value = binom.test(n_optimal_old_choices, n_responses, alternative = "greater")$p.value
  ) |>
  ungroup()

clean_df <- old_trials_df |> 
  left_join(binom_test_df) |>
  filter(p.value < .05) |>
  mutate(
    old_value_c = old_value - .5,
    old_image_name = if_else(old_side == "left", left_image_name, right_image_name),
    new_image_name = if_else(old_side == "left", right_image_name, left_image_name),
    memorability_bin = ordered(memorability_bin, levels = c("low", "mid", "high")),
    old_value_fct = factor(old_value),
    response_type = if_else(optimal_choice == 1, "Correct", "Error"),
    response_type_c = if_else(optimal_choice == 1, 1, -1),
    log_rt = log(rt)
  )

sub_choice_plot_df <- clean_df |>
  group_by(participant_id, memorability_bin, old_value_fct) |>
  summarize(
    p_old_chosen = mean(old_chosen)
  )
sub_choice_plot_df |>
  ggplot(aes(x = old_value_fct, y = p_old_chosen, 
             color = memorability_bin, group = memorability_bin)) +
  stat_summary(position = position_dodge(.2)) +
  stat_summary(geom = "line", position = position_dodge(.2)) +
  theme_classic() +
  labs(x = "Old Value", y = "P(Old)", color = "Memorability")

sub_choice_plot_df <- clean_df |>
  group_by(participant_id, memorability_bin, old_value_fct, old_side) |>
  summarize(
    p_old_chosen = mean(old_chosen)
  )
sub_choice_plot_df |>
  ggplot(aes(x = old_value_fct, y = p_old_chosen, 
             color = memorability_bin, group = memorability_bin)) +
  stat_summary(position = position_dodge(.2)) +
  stat_summary(geom = "line", position = position_dodge(.2)) +
  theme_classic() +
  facet_wrap(vars(old_side), labeller = label_both) +
  labs(x = "Old Value", y = "P(Old)", color = "Memorability")

sub_rt_plot_df <- clean_df |>
  filter_out(is.na(response_type)) |>
  group_by(participant_id, memorability_bin, old_value_fct, response_type) |>
  summarize(
    log_rt = mean(log_rt)
  )
sub_rt_plot_df |>
  ggplot(aes(x = old_value_fct, y = log_rt, 
             color = memorability_bin, linetype = response_type, 
             group = interaction(memorability_bin, response_type))) +
  stat_summary(position = position_dodge(.2)) +
  stat_summary(geom = "line", position = position_dodge(.2)) +
  theme_classic() +
  labs(x = "Old Value", y = "Log(RT)", color = "Memorability", linetype = "Response")

sub_rt_plot_df <- clean_df |>
  filter_out(is.na(response_type)) |>
  group_by(participant_id, memorability_bin, old_value_fct, response_type, old_side) |>
  summarize(
    log_rt = mean(log_rt)
  )
sub_rt_plot_df |>
  ggplot(aes(x = old_value_fct, y = log_rt, 
             color = memorability_bin, linetype = response_type,
             group = interaction(memorability_bin, response_type))) +
  stat_summary(position = position_dodge(.2)) +
  stat_summary(geom = "line", position = position_dodge(.2)) +
  theme_classic() +
  facet_wrap(vars(old_side), labeller = label_both) +
  labs(x = "Old Value", y = "RT", color = "Memorability", linetype = "Response")

m1 <- glmer(old_chosen ~ old_value_c * memorability_bin + 
              (old_value_c * memorability_bin | participant_id) + 
              (1 | old_image_name) + (1 | new_image_name), 
            family = binomial, data = clean_df)

rt_m1 <- lmer(log_rt ~ response_type_c * old_value_c * memorability_bin + 
       (response_type_c * old_value_c * memorability_bin | participant_id) + (1 | old_image_name), 
     data = clean_df)
