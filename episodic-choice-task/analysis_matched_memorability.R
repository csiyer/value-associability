library(tidyverse)

episodic_choice_data <- read_csv("~/Documents/GitHub/value-associability/episodic-choice-task/data/episodic_choice_data-matched_memorability.csv")

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
    memorability_bin = ordered(memorability_bin, levels = c("low", "high")),
    response_type = if_else(optimal_choice == 1, "Correct", "Error"),
    response_type_fct = factor(response_type, levels = c("Error", "Correct")),
    response_type_c = if_else(optimal_choice == 1, 1, -1),
    high_image = if_else(left_value == 1, left_image_name, right_image_name),
    low_image = if_else(left_value == 0, left_image_name, right_image_name),
    log_rt = log(rt)
  )

sub_choice_plot_df <- clean_df |>
  group_by(participant_id, memorability_bin) |>
  summarize(
    p_correct = mean(optimal_choice)
  )
sub_choice_plot_df |>
  ggplot(aes(x = memorability_bin, y = p_correct)) +
  stat_summary(position = position_dodge(.2)) +
  # stat_summary(geom = "line", position = position_dodge(.2)) +
  theme_classic() +
  labs(y = "P(Correct)", x = "Memorability")

sub_rt_plot_df <- clean_df |>
  filter_out(is.na(response_type)) |>
  group_by(participant_id, memorability_bin, response_type) |>
  summarize(
    log_rt = mean(log_rt)
  )
sub_rt_plot_df |>
  ggplot(aes(x = memorability_bin, y = log_rt, 
             color = response_type, group = response_type)) +
  stat_summary(position = position_dodge(.2)) +
  stat_summary(geom = "line", position = position_dodge(.2)) +
  theme_classic() +
  labs(x = "Memorability", y = "Log(RT)", color = "Response")

clean_df <- clean_df |> 
  mutate(
    high_image = if_else(left_value == 1, left_image_name, right_image_name),
    low_image = if_else(left_value == 0, left_image_name, right_image_name)
  )

m1 <- glmer(response_type_fct ~ memorability_bin + 
        (memorability_bin | participant_id) + 
        (1 | high_image) + (1 | low_image), 
      family = binomial, data = clean_df)
m1 <- glmer(response_type_fct ~ memorability_bin + 
              (memorability_bin | participant_id) + 
              (1 | high_image), 
            family = binomial, data = clean_df)

