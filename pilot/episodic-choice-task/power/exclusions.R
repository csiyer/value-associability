library(tidyverse)

truthy <- function(x) tolower(trimws(as.character(x))) %in% c("true", "1", "yes")

# Replicates episodic-choice-task/scripts/count_participants.py's exclusion logic in R
# (binomial-test version -- see scripts/count_participants.py and analysis.ipynb).
get_included_pids <- function(df, task_type = c("main", "mixed", "matched", "direct")) {
  task_type <- match.arg(task_type)
  is_direct <- task_type == "direct"

  df$is_attention_check <- truthy(df$is_attention_check)
  df$is_choice_trial <- truthy(df$is_choice_trial)
  if ("is_recognition_trial" %in% names(df)) df$is_recognition_trial <- truthy(df$is_recognition_trial)
  if ("is_value_test_trial" %in% names(df)) df$is_value_test_trial <- truthy(df$is_value_test_trial)
  if ("choice_missed" %in% names(df)) df$choice_missed <- truthy(df$choice_missed)
  df$correct <- as.numeric(truthy(df$correct))

  attention_df <- df |> filter(is_attention_check == TRUE)

  space_df <- attention_df |> filter(experiment_id == "episodic_choice_v3", response_key == " ")
  x_df <- attention_df |> filter(experiment_id != "episodic_choice_v3", response_key == "x" | response == "x")
  ai_pids <- unique(c(space_df$participant_id, x_df$participant_id))

  attn_perf <- attention_df |> group_by(participant_id) |> summarize(correct = mean(correct, na.rm = TRUE), .groups = "drop")
  failed_attn_pids <- attn_perf |> filter(correct < 1) |> pull(participant_id)

  if (is_direct) {
    old_trials_df <- df |> filter(is_recognition_trial == TRUE) |> filter(!is.na(recognition_correct))
    chance_col <- "recognition_correct"
  } else {
    old_trials_df <- df |> filter(old_trial == 1) |> filter(!is.na(optimal_old_choice))
    chance_col <- "optimal_old_choice"
  }
  # One-sample binomial test per subject against chance (0.5), one-tailed --
  # exact test for a proportion of binary outcomes (see chat: binomial vs.
  # t-test discussion). Replaces the previous t.test-based screen.
  binom_test_df <- old_trials_df |>
    group_by(participant_id) |>
    summarize(
      k = sum(.data[[chance_col]]),
      n = n(),
      p = tryCatch(binom.test(k, n, p = 0.5, alternative = "greater")$p.value, error = function(e) NA_real_),
      .groups = "drop"
    )
  at_chance_pids <- binom_test_df |> filter(is.na(p) | p >= 0.05) |> pull(participant_id)

  incomplete_pids <- c()
  if (is_direct) {
    incomplete_pids <- df |> filter(is_recognition_trial == TRUE) |> count(participant_id) |> filter(n < 100) |> pull(participant_id)
  } else if (task_type %in% c("mixed", "matched")) {
    incomplete_pids <- df |> filter(old_trial == 1) |> count(participant_id) |> filter(n < 70) |> pull(participant_id)
  }

  miss_rate_pids <- c()
  if (is_direct) {
    recog_miss <- df |> filter(is_recognition_trial == TRUE) |>
      group_by(participant_id) |> summarize(m = mean(as.numeric(choice_missed), na.rm = TRUE), .groups = "drop")
    value_miss <- df |> filter(is_value_test_trial == TRUE) |>
      group_by(participant_id) |> summarize(m = mean(as.numeric(value_test_missed), na.rm = TRUE), .groups = "drop")
    miss_rate_pids <- unique(c(
      recog_miss |> filter(m > 0.2) |> pull(participant_id),
      value_miss |> filter(m > 0.2) |> pull(participant_id)
    ))
  }

  all_pids <- unique(df$participant_id)
  excluded <- unique(c(ai_pids, failed_attn_pids, at_chance_pids, incomplete_pids, miss_rate_pids))
  included <- setdiff(all_pids, excluded)

  list(
    total = length(all_pids),
    included = length(included),
    included_pids = included,
    n_ai = length(ai_pids), n_failed_attn = length(failed_attn_pids),
    n_at_chance = length(at_chance_pids), n_incomplete = length(incomplete_pids),
    n_miss_rate = length(miss_rate_pids)
  )
}
