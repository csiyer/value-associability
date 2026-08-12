library(osfr)
library(tidyverse)
library(lme4)

data_dir <- "~/Documents/GitHub/value-associability/episodic-choice-task/data"
osf_retrieve_node("8d2cb") |>
  osf_ls_files() |>
  filter(name == "direct") |> 
  osf_download(path = data_dir, recurse = TRUE, conflicts = "skip")

# analysis ----------------------------------------------------------------

data_dir <- "~/Documents/GitHub/value-associability/episodic-choice-task/data"
filepaths <- list.files(file.path(data_dir, "direct"), full.names = TRUE)
# read_csv(filepaths, id = "file")
direct_df <- filepaths |> 
  map(~ read_csv(.x, col_types = cols(.default = col_character()))) |> 
  list_rbind(names_to = "file") |> 
  type_convert()

FAILED_ATTENTION_PIDS <- direct_df |> 
  filter(is_attention_check) |> 
  group_by(participant_id) |> 
  summarize(correct = mean(success)) |>
  filter(correct < .8)

old_trials_df <- direct_df |>
  filter_out(when_any(participant_id %in% FAILED_ATTENTION_PIDS, is.na(participant_id), is.na(old_trial), old_trial != 1)) |>
  select(-n_recognition_correct)

binom_test_df <- old_trials_df |>
  filter(is_recognition_trial) |>
  group_by(participant_id) |>
  summarize(
    n_recognition_correct = sum(recognition_correct),
    n_responses = n()
  ) |>
  rowwise() |>
  mutate(
    p.value = binom.test(n_recognition_correct, n_responses, alternative = "greater")$p.value
  ) |>
  ungroup()

clean_df <- old_trials_df |> 
  left_join(binom_test_df) |>
  filter(p.value < .05) |>
  mutate(
    old_value_c = old_value - .5,
    old_image_name = if_else(old_side == "left", left_image_name, right_image_name),
    memorability_bin = ordered(memorability_bin, levels = c("low", "mid", "high")),
    memorability_num = as.numeric(memorability_bin) - 2,
    old_value_fct = factor(old_value)
  )

memory_test_trials_df <- clean_df |>
  select(participant_id, trial_number, old_image_name, old_value_c, 
         memorability_bin, memorability_num, old_value_fct, old_side, recognition_correct, value_test_correct,
         value_test_response, response) |>
  group_by(participant_id, trial_number) |>
  mutate(
    value_test_correct = replace_when(value_test_correct, response == "null" ~ NA),
    recognition_correct = replace_when(recognition_correct, response == "null" ~ NA),
    value_test_response = as.numeric(lead(value_test_response)),
    value_test_correct = lead(value_test_correct),
    recognition_correct_str = if_else(recognition_correct == 1, "Recognized", "Not Recognized"),
    recognition_correct_c = if_else(recognition_correct == 1, .5, -.5)
  ) |> filter_out(is.na(old_image_name))
  
# Recognition -------------------------------------------------------------

# recognition_df <- clean_df |>
#   filter(is_recognition_trial)

sub_recognition_plot_df <- memory_test_trials_df |>
  group_by(participant_id, memorability_bin, old_value_fct) |>
  summarize(
    p_recognition_correct = mean(recognition_correct)
  )
sub_recognition_plot_df |>
  ggplot(aes(x = old_value_fct, y = p_recognition_correct, 
             color = memorability_bin, group = memorability_bin)) +
  stat_summary(position = position_dodge(.2)) +
  stat_summary(geom = "line", position = position_dodge(.2)) +
  theme_classic() +
  labs(x = "Value", y = "P(Recognition)", color = "Memorability")
sub_recognition_plot_df |>
  ggplot(aes(x = memorability_bin, y = p_recognition_correct, 
             color = old_value_fct, group = old_value_fct)) +
  stat_summary(position = position_dodge(.2)) +
  stat_summary(geom = "line", position = position_dodge(.2)) +
  theme_classic() +
  labs(x = "Memorability", y = "P(Recognition)", color = "Value")

# Value Recall ------------------------------------------------------------

# value_recall_df <- clean_df |>
#   filter(is_value_test_trial)

sub_value_recall_plot_df <- memory_test_trials_df |>
  group_by(participant_id, memorability_bin, old_value_fct) |>
  summarize(
    p_value_recall_correct = mean(value_test_correct)
  )
sub_value_recall_plot_df |>
  ggplot(aes(x = memorability_bin, y = p_value_recall_correct , 
             color = old_value_fct, group = old_value_fct)) +
  stat_summary(position = position_dodge(.2)) +
  stat_summary(geom = "line", position = position_dodge(.2)) +
  theme_classic() +
  labs(x = "Memorability", y = "P(Value Recall)", color = "Value")
sub_value_recall_plot_df |>
  ggplot(aes(x = old_value_fct, y = p_value_recall_correct, 
             color = memorability_bin, group = memorability_bin)) +
  stat_summary(position = position_dodge(.2)) +
  stat_summary(geom = "line", position = position_dodge(.2)) +
  theme_classic() +
  labs(x = "Old Value", y = "P(Value Recall)", color = "Memorability")

# P(Recall)
sub_value_recall_plot_df <- memory_test_trials_df |>
  filter_out(is.na(recognition_correct_str)) |>
  group_by(participant_id, memorability_bin, old_value_fct, recognition_correct_str) |>
  summarize(
    p_value_recall_correct = mean(value_test_correct)
  )
sub_value_recall_plot_df |>
  ggplot(aes(x = memorability_bin, y = p_value_recall_correct, 
             color = old_value_fct, group = old_value_fct)) +
  stat_summary(position = position_dodge(.2)) +
  stat_summary(geom = "line", position = position_dodge(.2)) +
  theme_classic() +
  facet_wrap(vars(recognition_correct_str)) +
  labs(x = "Memorability", y = "P(Value Recall)", color = "Value")

# P(Recall 1)
sub_value_recall_1_plot_df <- memory_test_trials_df |>
  filter_out(is.na(recognition_correct_str)) |>
  group_by(participant_id, memorability_bin, old_value_fct, recognition_correct_str) |>
  summarize(
    p_value_recall_1 = mean(value_test_response)
  )
sub_value_recall_1_plot_df |>
  ggplot(aes(x = memorability_bin, y = p_value_recall_1, 
             color = old_value_fct, group = old_value_fct)) +
  stat_summary(position = position_dodge(.2)) +
  stat_summary(geom = "line", position = position_dodge(.2)) +
  theme_classic() +
  facet_wrap(vars(recognition_correct_str)) +
  labs(x = "Memorability", y = 'P(Value Recall "1")', color = "Value")

m1 <- glmer(value_test_correct ~ memorability_num + 
              (memorability_num || participant_id) + (1 | old_image_name), 
            family = binomial, data = memory_test_trials_df)
m2 <- glmer(value_test_correct ~ old_value_c * memorability_num + 
              (old_value_c * memorability_num || participant_id) + (old_value_c || old_image_name), 
            family = binomial, data = memory_test_trials_df)
m3 <- glmer(value_test_correct ~ old_value_c * memorability_num + 
              (old_value_c * memorability_num || participant_id) + (old_value_c || old_image_name), 
            family = binomial, data = memory_test_trials_df |> filter(recognition_correct == 1))
