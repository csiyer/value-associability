library(tidyverse)

episodic_choice_data <- read_csv("~/Documents/GitHub/value-associability/episodic-choice-task/data/episodic_choice_data-mixed_memorability.csv")

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
  filter(left_value == right_value) |>
  mutate(
    left_mem_bin = ordered(left_mem_bin, levels = c("low", "high")),
    right_mem_bin = ordered(right_mem_bin, levels = c("low", "high")),
    right_value_fct = factor(right_value),
    chose_right = chosen_side == "right",
    chose_high_mem = if_else(chose_right != left_is_high, TRUE, FALSE)
  )

# Matched value
sub_choice_plot_df <- clean_df |>
  group_by(participant_id, right_mem_bin, right_value_fct) |>
  summarize(
    p_right = mean(chose_right, na.rm = TRUE)
  )
sub_choice_plot_df |>
  ggplot(aes(x = right_mem_bin, y = p_right, color = right_value_fct, group = right_value_fct)) +
  stat_summary(position = position_dodge(.2)) +
  theme_classic() +
  labs(y = "P(Choose Right)", x = "Memorability of Right Option", color = "Overall Value")
sub_choice_plot_df |>
  ggplot(aes(x = right_value_fct, y = p_right, color = right_mem_bin, group = right_mem_bin)) +
  stat_summary(position = position_dodge(.2)) +
  stat_summary(geom = "line", position = position_dodge(.2)) +
  theme_classic() +
  labs(y = "P(Choose Right)", x = "Overall Value", color = "Memorability of Right Option")

sub_choice_plot_df <- clean_df |>
  group_by(participant_id, right_value_fct) |>
  summarize(
    p_high_mem = mean(chose_high_mem, na.rm = TRUE)
  )
sub_choice_plot_df |>
  ggplot(aes(x = right_value_fct, y = p_high_mem)) +
  stat_summary(position = position_dodge(.2)) +
  theme_classic() +
  labs(y = "P(Choose High Memorability)", x = "Overall Value")

sub_rt_plot_df <- clean_df |>
  mutate(
    chosen_mem_str = if_else(chose_high_mem, "High", "Low")
  ) |>
  filter_out(is.na(chosen_mem_str)) |>
  group_by(participant_id, right_value_fct, chosen_mem_str) |>
  summarize(
    rt = mean(rt)
  )
sub_rt_plot_df |>
  ggplot(aes(x = right_value_fct, y = rt, 
             color = chosen_mem_str, group = chosen_mem_str)) +
  stat_summary(position = position_dodge(.2)) +
  stat_summary(geom = "line", position = position_dodge(.2)) +
  theme_classic() +
  labs(x = "Overall Value", y = "RT", color = "Chosen Memorability")
