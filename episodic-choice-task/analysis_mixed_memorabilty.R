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
  mutate(
    left_mem_bin = ordered(left_mem_bin, levels = c("low", "high")),
    right_mem_bin = ordered(right_mem_bin, levels = c("low", "high")),
    right_value_fct = factor(right_value),
    left_value_fct = factor(left_value),
    overall_value = (left_value + right_value) - 1, # Centered
    chose_right = chosen_side == "right",
    high_mem_image = if_else(left_is_high, left_image_name, right_image_name),
    low_mem_image = if_else(left_is_high, right_image_name, left_image_name),
    chose_high_mem = if_else(chose_right != left_is_high, TRUE, FALSE)
  )

# Matched value -----------------------------------------------------------

matched_value_clean_df <- clean_df |>
  filter(left_value == right_value)

sub_choice_plot_df <- matched_value_clean_df |>
  group_by(participant_id, right_mem_bin, right_value_fct) |>
  summarize(
    p_right = mean(chose_right, na.rm = TRUE)
  )
sub_choice_plot_df |>
  ggplot(aes(x = right_mem_bin, y = p_right, color = right_value_fct, group = right_value_fct)) +
  stat_summary(position = position_dodge(.2)) +
  stat_summary(geom = "line", position = position_dodge(.2)) +
  theme_classic() +
  labs(y = "P(Choose Right)", x = "Memorability of Right Option", color = "Overall Value")

sub_choice_plot_df <- matched_value_clean_df |>
  group_by(participant_id, right_value_fct) |>
  summarize(
    p_high_mem = mean(chose_high_mem, na.rm = TRUE)
  )
sub_choice_plot_df |>
  ggplot(aes(x = right_value_fct, y = p_high_mem)) +
  stat_summary(position = position_dodge(.2)) +
  theme_classic() +
  labs(y = "P(Choose High Memorability)", x = "Overall Value")

sub_rt_plot_df <- matched_value_clean_df |>
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

sub_rt_plot_df <- matched_value_clean_df |>
  filter_out(is.na(chosen_side)) |>
  group_by(participant_id, right_value_fct, left_mem_bin, right_mem_bin, chosen_side) |>
  summarize(
    rt = mean(rt)
  )

sub_rt_plot_df |>
  ggplot(aes(x = right_mem_bin, y = rt, 
             color = chosen_side, group = chosen_side)) +
  stat_summary(position = position_dodge(.2)) +
  stat_summary(geom = "line", position = position_dodge(.2)) +
  theme_classic() +
  facet_wrap(vars(right_value_fct)) +
  labs(x = "Memorability of Right Option", y = "RT", color = "Chosen Side")

m1 <- glmer(chose_high_mem ~ overall_value + 
        (overall_value || participant_id) + 
        (1 | high_mem_image) + 
        (1 | low_mem_image), 
      family = binomial,
      data = matched_value_clean_df)

# Mixed Value -------------------------------------------------------------

mixed_value_clean_df <- clean_df |>
  filter(left_value != right_value) |>
  mutate(
    high_value_side = if_else(left_value > right_value, "left", "right"),
    optimal_choice_str = if_else(optimal_choice == 1, "Correct", "Error")
  )

sub_choice_plot_df <- mixed_value_clean_df |>
  group_by(participant_id, right_mem_bin, right_value_fct) |>
  summarize(
    p_right = mean(chose_right, na.rm = TRUE)
  )
sub_choice_plot_df |>
  ggplot(aes(x = right_value_fct, y = p_right, color = right_mem_bin, group = right_mem_bin)) +
  stat_summary(position = position_dodge(.2)) +
  stat_summary(geom = "line", position = position_dodge(.2)) +
  theme_classic() +
  labs(y = "P(Choose Right)", x = "Right Value", color = "Right Memorability")

sub_rt_plot_df <- mixed_value_clean_df |>
  filter_out(is.na(chosen_side)) |>
  group_by(participant_id, high_value_side, left_mem_bin, right_mem_bin, chosen_side) |>
  summarize(
    rt = mean(rt)
  )
sub_rt_plot_df |>
  ggplot(aes(x = right_mem_bin, y = rt, 
             color = chosen_side, group = chosen_side)) +
  stat_summary(position = position_dodge(.2)) +
  stat_summary(geom = "line", position = position_dodge(.2)) +
  theme_classic() +
  facet_wrap(vars(high_value_side)) +
  labs(x = "Memorability of Right Option", y = "RT", color = "Chosen Side")

sub_rt_plot_df <- mixed_value_clean_df |>
  filter_out(is.na(chosen_side)) |>
  group_by(participant_id, optimal_choice_str, right_value_fct, right_mem_bin) |>
  summarize(
    rt = mean(rt)
  )
sub_rt_plot_df |>
  ggplot(aes(x = right_value_fct, y = rt, 
             color = right_mem_bin, linetype = optimal_choice_str, 
             group = interaction(right_mem_bin, optimal_choice_str))) +
  stat_summary(position = position_dodge(.2)) +
  stat_summary(geom = "line", position = position_dodge(.2)) +
  theme_classic() +
  # facet_wrap(vars(optimal_choice_str)) +
  labs(x = "Right Value", y = "RT", color = "Right Memorability", linetype = "Response")
