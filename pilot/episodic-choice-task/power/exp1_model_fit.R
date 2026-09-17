library(tidyverse)
library(glmmTMB)
source("power/exclusions.R")

df <- read.csv("data/episodic_choice_data.csv", stringsAsFactors = FALSE)
res <- get_included_pids(df, "main")
cat("Included N:", res$included, "\n")

df$old_chosen <- as.numeric(df$old_chosen)

old_df <- df |>
  filter(participant_id %in% res$included_pids, old_trial == 1) |>
  mutate(
    old_value_c = old_value - 0.5,
    old_image_name = if_else(old_side == "left", left_image_name, right_image_name),
    memorability_bin = factor(memorability_bin, levels = c("low", "mid", "high"), ordered = FALSE)
  ) |>
  filter(!is.na(old_chosen), !is.na(old_value_c), !is.na(memorability_bin))

cat("N trials:", nrow(old_df), " N participants:", n_distinct(old_df$participant_id), "\n")

# Diagonal/uncorrelated random-effects structure (the maximal correlated
# structure did not converge in lme4 in a practical amount of time -- see
# preregistration "Statistical Models > Experiment 1"). Fit with glmmTMB.
t0 <- Sys.time()
m_diag <- glmmTMB(
  old_chosen ~ old_value_c * memorability_bin +
    (old_value_c * memorability_bin || participant_id) + (old_value_c || old_image_name),
  family = binomial, data = old_df
)
cat("glmmTMB model fit time:", as.numeric(Sys.time() - t0, units = "secs"), "s\n")
print(summary(m_diag))
saveRDS(m_diag, "power/exp1_model_fit.rds")
