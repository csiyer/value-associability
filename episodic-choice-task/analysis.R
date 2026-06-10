library(tidyverse)

episodic_choice_data <- read_csv("~/Documents/GitHub/value-associability/episodic-choice-task/data/episodic_choice_data.cs")

sub_old_df <- episodic_choice_data |>
  filter(old_trial == 1) |>
  mutate(
    old_value = factor(old_value)
  ) |>
  group_by(participant_id, memorability_bin, old_value) |>
  dplyr::summarize(
    p_old_chosen = mean(old_chosen)
  )
sub_old_df |>
  ggplot(aes(x = old_value, y = p_old_chosen, 
             color = memorability_bin, group = memorability_bin)) +
  stat_summary(position = position_dodge(.2)) +
  stat_summary(geom = "line", position = position_dodge(.2)) +
  theme_classic() +
  labs(x = "Old Value", y = "P(Old)", color = "Memorability")

episodic_choice_data <- episodic_choice_data |>
  mutate(
    old_value_c = old_value - .5,
    old_image_name = if_else(old_side == "left", left_image_name, right_image_name),
    memorability_bin = ordered(memorability_bin, levels = c("low", "mid", "high"))
  )

m1 <- glmer(old_chosen ~ old_value_c * memorability_bin + 
              (1 | participant_id) + (1 | old_image_name), 
            family = binomial, data = episodic_choice_data)

m2 <- glmer(old_chosen ~ old_value_c * memorability_bin + 
              diag(old_value_c | participant_id) + diag(old_value_c | old_image_name), 
            family = binomial, data = episodic_choice_data)

m3 <- glmer(old_chosen ~ old_value_c * memorability_bin + 
              diag(old_value_c + memorability_bin | participant_id) + diag(old_value_c | old_image_name), 
            family = binomial, data = episodic_choice_data)

m4 <- glmer(old_chosen ~ old_value_c * memorability_bin + 
              diag(old_value_c * memorability_bin | participant_id) + diag(old_value_c | old_image_name), 
            family = binomial, data = episodic_choice_data)

m5 <- glmer(old_chosen ~ old_value_c * memorability_bin + 
              (old_value_c * memorability_bin | participant_id) + (old_value_c | old_image_name), 
            family = binomial, data = episodic_choice_data)
summary(m5)

m6 <- glmer(old_chosen ~ old_value_c * memorability_bin + 
              (old_value_c * memorability_bin | participant_id) + (1 | old_image_name), 
            family = binomial, data = episodic_choice_data)
anova(m6, m5)
