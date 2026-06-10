library(tidyverse)

source("li_preprocess_1B.R")

qnorm_breaks5 <- c(qnorm(0), qnorm(.2), qnorm(.4), qnorm(.6), qnorm(.8), qnorm(1))
abs_qnorm_breaks5 <- c(qnorm(.49), qnorm(.6), qnorm(.7), qnorm(.8), qnorm(.9), qnorm(1))

# Use only close value trials
delta.mem.choice.sub.df <- choice.low.v |>
  mutate(
    delta.mem.z = delta.mem / sd(delta.mem),
    delta.mem.5 = ordered(cut(delta.mem.z, breaks = qnorm_breaks5, labels = FALSE)),
    SumValue3 = ordered(ntile(SumValue, 3))
  ) |>
  group_by(ID, delta.mem.5, SumValue3) |>
  summarize(
    p_right = mean(choseright)
  ) |>
  ungroup()
# Make sure all subs contribute to every bin
bad_combs <- delta.mem.choice.sub.df |>
  count(ID, delta.mem.5, SumValue3, .drop = FALSE) |>
  filter(n == 0) |>
  distinct(ID)
delta.mem.choice.sub.df |> 
  anti_join(bad_combs) |>
  ggplot(aes(delta.mem.5, p_right, color = SumValue3, group = SumValue3)) +
  stat_summary(position = position_dodge(width = 0.2)) +
  stat_summary(geom = "line", position = position_dodge(width = 0.2)) +
  labs(y = "P(Right)", color = "Overall Value") +
  scale_x_discrete(
    "Difference in Memorability (Right - Left)",
    labels = c(
      "1" = "Low",
      "2" = "",
      "3" = "Mid",
      "4" = "",
      "5" = "High"
    )
  ) +
  theme_classic() +
  scale_color_discrete(labels = c("Low", "Medium", "High"))

delta.mem.rt.sub.df <- choice.low.v |>
  mutate(
    delta.mem.z = delta.mem / sd(delta.mem),
    abs.delta.mem.5 = ordered(cut(abs(delta.mem.z), breaks = abs_qnorm_breaks5, labels = FALSE)),
    SumValue3 = ordered(ntile(SumValue, 3))
  ) |>
  group_by(ID, abs.delta.mem.5, SumValue3) |>
  summarize(
    rt = mean(rt)
  ) |>
  ungroup()
delta.mem.rt.sub.df |> 
  anti_join(bad_combs) |>
  ggplot(aes(abs.delta.mem.5, rt, color = SumValue3, group = SumValue3)) +
  stat_summary(position = position_dodge(width = 0.2)) +
  stat_summary(geom = "line", position = position_dodge(width = 0.2)) +
  labs(y = "RT", color = "Overall Value") +
  scale_x_discrete(
    "Abs(Difference in Memorability)",
    labels = c(
      "1" = "Low",
      "2" = "",
      "3" = "Mid",
      "4" = "",
      "5" = "High"
    )
  ) +
  theme_classic() +
  scale_color_discrete(labels = c("Low", "Medium", "High"))

delta.mem.chosen.rt.sub.df <- choice.low.v |>
  mutate(
    delta.mem.chosen5 = ordered(ntile(delta.mem.chosen, 5)),
    SumValue3 = ordered(ntile(SumValue, 3))
  ) |>
  group_by(ID, delta.mem.chosen5, SumValue3) |>
  summarize(
    rt = mean(rt)
  ) |>
  ungroup()
delta.mem.chosen.rt.sub.df |> 
  anti_join(bad_combs) |>
  ggplot(aes(delta.mem.chosen5, rt, color = SumValue3, group = SumValue3)) +
  stat_summary(position = position_dodge(width = 0.2)) +
  stat_summary(geom = "line", position = position_dodge(width = 0.2)) +
  labs(y = "RT", color = "Overall Value") +
  scale_x_discrete(
    "Difference in Memorability (Chosen - Unchosen)",
    labels = c(
      "1" = "Low",
      "2" = "",
      "3" = "Mid",
      "4" = "",
      "5" = "High"
    )
  ) +
  theme_classic() +
  scale_color_discrete(labels = c("Low", "Medium", "High"))

# Models ------------------------------------------------------------------

m1_right_low.v_ns1 <- glmer(choseright ~ delta.mem * scale(SumValue) + 
                               (delta.mem * scale(SumValue) || ID) + (1 | stim_left) +
                               (1 | stim_right),
                             family = "binomial",
                             data = choice.low.v)

# assume that difference in value is actually 0 so sign of dM is potentially wrong.
m1_log_rt_low.v_ns1 <- lmer(log_rt ~ scale(abs.delta.mem) * scale(SumValue) + 
                          (scale(abs.delta.mem) * scale(SumValue) || ID) + (1 | stim_left) +
                          (1 | stim_right),
                        data = choice.low.v)

m1_log_rt_chosen_low.v_ns1 <- lmer(log_rt ~ delta.mem.chosen * scale(SumValue) + 
                              (delta.mem.chosen * scale(SumValue) || ID) + (1 | stim_left) +
                              (1 | stim_right),
                            data = choice.low.v)

m2_right_all_ns1 <- glmer(choseright ~ delta.mem * scale(SumValue) + z.delta.value * scale(SumMem) +
                        (delta.mem * scale(SumValue) + z.delta.value * scale(SumMem) || ID) + (1 | stim_left) +
                        (1 | stim_right),
                      family = "binomial",
                      data = choice.z)

m2_log_rt_high.v_ns1 <- lmer(log_rt ~ dM * scale(SumValue) + scale(abs.delta.v.z) * scale(SumMem) + 
                              (dM * scale(SumValue) + scale(abs.delta.v.z) * scale(SumMem) || ID) + (1 | stim_left) +
                              (1 | stim_right),
                            data = choice.high.v)

m2_log_rt_chosen_all_ns1 <- lmer(log_rt ~ delta.mem.chosen * scale(SumValue) + delta.v.z.chosen * scale(SumMem) + 
                                     (delta.mem.chosen * scale(SumValue) + delta.v.z.chosen * scale(SumMem) || ID) + (1 | stim_left) +
                                     (1 | stim_right),
                                   data = choice.low.v)
