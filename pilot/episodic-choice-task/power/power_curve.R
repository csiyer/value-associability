library(tidyverse)
library(glmmTMB)
library(parallel)

fit <- readRDS("power/exp1_model_fit.rds")
d <- fit$frame
full_pids <- unique(as.character(d$participant_id))
cat("Full N participants:", length(full_pids), "N rows:", nrow(d), "\n")

TARGET_COEF <- "old_value_c:memorability_binhigh"
CANDIDATE_N <- c(15, 20, 30, 40, 50, 60, 80, 100)
N_SIM <- 150

refit_formula <- old_chosen ~ old_value_c * memorability_bin +
  (old_value_c * memorability_bin || participant_id) + (old_value_c || old_image_name)

one_replicate <- function(rep_i) {
  set.seed(1000 + rep_i)
  ysim <- simulate(fit, seed = 1000 + rep_i)[[1]]
  d_sim <- d
  d_sim$old_chosen <- ysim

  out_rows <- list()
  for (N in CANDIDATE_N) {
    sub_pids <- sample(full_pids, N, replace = FALSE)
    d_sub <- d_sim[d_sim$participant_id %in% sub_pids, ]
    m <- tryCatch(
      suppressWarnings(glmmTMB(refit_formula, family = binomial, data = d_sub)),
      error = function(e) NULL
    )
    p <- NA
    conv_ok <- FALSE
    if (!is.null(m)) {
      co <- tryCatch(summary(m)$coefficients$cond, error = function(e) NULL)
      if (!is.null(co) && TARGET_COEF %in% rownames(co)) {
        p <- co[TARGET_COEF, "Pr(>|z|)"]
        conv_ok <- !is.null(m$sdr) && m$sdr$pdHess
      }
    }
    out_rows[[length(out_rows) + 1]] <- data.frame(rep = rep_i, N = N, p = p, conv_ok = conv_ok)
  }
  do.call(rbind, out_rows)
}

t0 <- Sys.time()
results_list <- mclapply(seq_len(N_SIM), one_replicate, mc.cores = 7)
cat("Total time:", as.numeric(Sys.time() - t0, units = "secs"), "s\n")

results <- do.call(rbind, results_list)
write.csv(results, "power/power_curve_results.csv", row.names = FALSE)

summary_df <- results |>
  group_by(N) |>
  summarize(
    n_reps = n(),
    n_converged = sum(conv_ok, na.rm = TRUE),
    power = mean(p < .05, na.rm = TRUE),
    .groups = "drop"
  )
print(summary_df)
write.csv(summary_df, "power/power_curve_summary.csv", row.names = FALSE)
