if (typeof CanvasRenderingContext2D.prototype.roundRect !== "function") {
    CanvasRenderingContext2D.prototype.roundRect = function (x, y, width, height, radius) {
        const r = typeof radius === "number"
            ? { tl: radius, tr: radius, br: radius, bl: radius }
            : Object.assign({ tl: 0, tr: 0, br: 0, bl: 0 }, radius);
        this.beginPath();
        this.moveTo(x + r.tl, y);
        this.lineTo(x + width - r.tr, y);
        this.quadraticCurveTo(x + width, y, x + width, y + r.tr);
        this.lineTo(x + width, y + height - r.br);
        this.quadraticCurveTo(x + width, y + height, x + width - r.br, y + height);
        this.lineTo(x + r.bl, y + height);
        this.quadraticCurveTo(x, y + height, x, y + height - r.bl);
        this.lineTo(x, y + r.tl);
        this.quadraticCurveTo(x, y, x + r.tl, y);
        this.closePath();
        return this;
    };
}

const IMAGE_CACHE = {};
const TASK_STATE = {
    availableStimuli: [],
    chosenHistory: [],
    imageValueMap: new Map(),
    currentTrial: null
};

function initTask(jsPsych, subject_id) {
    const timeline = [];
    const stimulusPool = jsPsych.randomization.shuffle(loadStimulusMetadata());

    if (stimulusPool.length < params.n_trials) {
        throw new Error(`Need at least ${params.n_trials} available stimuli.`);
    }

    TASK_STATE.availableStimuli = [...stimulusPool];
    const preloadImages = stimulusPool.map((stimulus) => `${params.stimuli_dir}/${stimulus.image_name}`);

    jsPsych.data.addProperties({
        experiment_id: params.experiment_id,
        subject_id: subject_id,
        possible_values: JSON.stringify(params.possible_values),
        old_trial_pct: params.old_trial_pct,
        min_trials_ago: params.min_trials_ago,
        max_trials_ago: params.max_trials_ago
    });

    timeline.push({
        type: jsPsychPreload,
        images: preloadImages,
        message: "Loading card images...",
        on_finish: function () {
            preloadImages.forEach((path) => {
                const img = new Image();
                img.src = path;
                IMAGE_CACHE[path] = img;
            });
        }
    });

    timeline.push({
        type: jsPsychFullscreen,
        fullscreen_mode: true,
        message: `<div class="instruction-container">
            <h2>Welcome</h2>
            <p>This study takes about <strong>${params.completion_time} minutes</strong>.</p>
            <p>You will earn a base payment of <strong>$${params.base_pay}</strong>, plus a bonus of up to <strong>$${params.max_bonus}</strong> based on your performance.</p>
            <p>Please note that you are participating in a scientific study. Your responses will be a huge help for our research, so we ask you give the study your best effort and attention. Thank you!</p>
        </div>`,
        button_label: "Enter fullscreen & begin"
    });

    timeline.push({
        type: jsPsychInstructions,
        pages: params.instruction_pages,
        show_clickable_nav: true,
        button_label_next: "Next",
        button_label_previous: "Back"
    });

    timeline.push(buildBlankCanvasTrial(params.iti));

    for (let trialIndex = 0; trialIndex < params.n_trials; trialIndex++) {
        timeline.push({
            type: jsPsychHtmlKeyboardResponse,
            stimulus: "",
            choices: "NO_KEYS",
            trial_duration: 0,
            on_start: function () {
                TASK_STATE.currentTrial = generateTrialSpec(jsPsych, trialIndex + 1);
            }
        });

        timeline.push({
            type: jsPsychCanvasKeyboardResponse,
            canvas_size: [850, 1200],
            choices: ["arrowleft", "arrowright"],
            trial_duration: params.choice_duration,
            data: {
                phase: "choice",
                is_choice_trial: true,
            },
            stimulus: function (canvas) {
                const ctx = canvas.getContext("2d");
                drawChoiceDisplay(ctx, TASK_STATE.currentTrial);
            },
            on_finish: function (data) {
                const trial = TASK_STATE.currentTrial;
                const responseKey = (data.response || "").toLowerCase();
                Object.assign(data, {
                    trial_number: trial.trial_number,
                    is_repeat_trial: trial.is_repeat_trial,
                    repeat_side: trial.repeat_side,
                    repeated_card_value: trial.repeated_card ? trial.repeated_card.value : null,
                    repeated_card_image_name: trial.repeated_card ? trial.repeated_card.image_name : null,
                    repeated_card_original_trial: trial.repeated_card ? trial.repeated_card.origin_trial_number : null,
                    left_image_name: trial.left.image_name,
                    left_image_path: trial.left.image_path,
                    left_image_memorability: trial.left.things_memorability,
                    left_value: trial.left.value,
                    left_is_repeat: trial.left.is_repeat,
                    right_image_name: trial.right.image_name,
                    right_image_path: trial.right.image_path,
                    right_image_memorability: trial.right.things_memorability,
                    right_value: trial.right.value,
                    right_is_repeat: trial.right.is_repeat
                });
                data.timestamp = new Date().toISOString();

                if (!responseKey) {
                    data.chosen_side = null;
                    data.chosen_value = null;
                    data.reward = 0;
                    data.did_choose_repeat = false;
                    data.optimal_repeat_choice = null;
                    return;
                }

                const chosenSide = responseKey === "arrowleft" ? "left" : "right";
                const unchosenSide = chosenSide === "left" ? "right" : "left";
                const chosenCard = trial[chosenSide];
                const repeatedCard = trial.repeated_card;

                data.chosen_side = chosenSide;
                data.unchosen_side = unchosenSide;
                data.chosen_image_name = chosenCard.image_name;
                data.chosen_image_path = chosenCard.image_path;
                data.chosen_image_memorability = chosenCard.things_memorability;
                data.chosen_value = chosenCard.value;
                data.reward = chosenCard.value;
                data.did_choose_repeat = trial.is_repeat_trial && chosenCard.is_repeat;

                TASK_STATE.chosenHistory.push({
                    image_name: chosenCard.image_name,
                    image_path: chosenCard.image_path,
                    things_file_path: chosenCard.things_file_path,
                    things_memorability: chosenCard.things_memorability,
                    things_category: chosenCard.things_category,
                    memorability_percentile: chosenCard.memorability_percentile,
                    value: chosenCard.value,
                    origin_trial_number: chosenCard.origin_trial_number,
                    chosen_trial_number: trial.trial_number,
                    has_repeated: false
                });

                if (trial.is_repeat_trial && repeatedCard) {
                    const shouldChooseRepeat = repeatedCard.value > 0.5;
                    data.optimal_repeat_choice =
                        (shouldChooseRepeat && data.did_choose_repeat) ||
                        (!shouldChooseRepeat && !data.did_choose_repeat);
                } else {
                    data.optimal_repeat_choice = null;
                }
            }
        });

        timeline.push({
            type: jsPsychCanvasKeyboardResponse,
            canvas_size: [850, 1200],
            choices: "NO_KEYS",
            trial_duration: function () {
                const lastData = jsPsych.data.get().last(1).values()[0];
                return lastData.response ? params.highlight_duration + params.flip_duration + params.revealed_duration : params.too_slow_duration;
            },
            stimulus: function (canvas) {
                const ctx = canvas.getContext("2d");
                const lastData = jsPsych.data.get().last(1).values()[0];
                drawFeedbackDisplay(ctx, TASK_STATE.currentTrial, lastData);
            }
        });

        timeline.push(buildBlankCanvasTrial(params.iti));
    }

    timeline.push({
        type: jsPsychHtmlButtonResponse,
        stimulus: function () {
            const summary = getRepeatSummary(jsPsych);
            return `<div class="instruction-container">
                <h2>Finished!</h2>
                <p>You made optimal choices on <strong>${(summary.optimalRate * 100).toFixed(1)}%</strong> of repeated-card trials.</p>
                <p>Your bonus is <strong>$${summary.bonus.toFixed(2)}</strong>.</p>
                <p>Your final pay is <strong>$${(params.base_pay + summary.bonus).toFixed(2)}</strong>.</p>
                <p>Thank you for your participation!</p>
            </div>`;
        },
        choices: ["Submit data & end experiment"],
        on_finish: function (data) {
            const summary = getRepeatSummary(jsPsych);
            data.is_summary = true;
            data.optimal_repeat_rate = summary.optimalRate;
            data.repeated_card_trials = summary.nRepeatTrials;
            data.optimal_repeat_trials = summary.nOptimal;
            data.final_bonus = summary.bonus.toFixed(2);
        }
    });

    timeline.push({
        type: jsPsychPipe,
        action: "save",
        experiment_id: params.data_pipe_id,
        filename: `${subject_id}.csv`,
        data_string: function () {
            return jsPsych.data.get().csv();
        },
        on_finish: function () {
            window.location.href = "https://app.prolific.com/submissions/complete?cc=" + params.prolific_completion_code;
        }
    });

    jsPsych.run(timeline);
}

function generateTrialSpec(jsPsych, trialNumber) {
    const eligibleRepeats = TASK_STATE.chosenHistory.filter((entry) => {
        const lag = trialNumber - entry.chosen_trial_number;
        return lag >= params.min_trials_ago && lag <= params.max_trials_ago && !entry.has_repeated;
    });

    const useRepeat = eligibleRepeats.length > 0 && Math.random() < params.old_trial_pct;
    const repeatEntry = useRepeat
        ? jsPsych.randomization.sampleWithoutReplacement(eligibleRepeats, 1)[0]
        : null;
    const repeatSide = repeatEntry
        ? jsPsych.randomization.sampleWithoutReplacement(["left", "right"], 1)[0]
        : null;

    if (repeatEntry) {
        repeatEntry.has_repeated = true;
    }

    const leftCard = repeatSide === "left"
        ? materializeRepeatedCard(repeatEntry)
        : materializeNewCard(jsPsych, trialNumber);
    const rightCard = repeatSide === "right"
        ? materializeRepeatedCard(repeatEntry)
        : materializeNewCard(jsPsych, trialNumber);

    return {
        trial_number: trialNumber,
        is_repeat_trial: Boolean(repeatEntry),
        repeat_side: repeatSide,
        repeated_card: repeatEntry,
        left: leftCard,
        right: rightCard
    };
}

function materializeCard(stimulus, isRepeat) {
    return {
        image_name: stimulus.image_name,
        image_path: `${params.stimuli_dir}/${stimulus.image_name}`,
        things_file_path: stimulus.things_file_path,
        things_memorability: Number(stimulus.things_memorability),
        things_category: stimulus.things_category,
        memorability_percentile: Number(stimulus.memorability_percentile),
        value: null,
        value_label: null,
        is_repeat: isRepeat,
        origin_trial_number: null
    };
}

function materializeNewCard(jsPsych, trialNumber) {
    const stimulus = TASK_STATE.availableStimuli.shift();
    if (!stimulus) {
        throw new Error("Ran out of new stimuli while building episodic choice trials.");
    }

    const card = materializeCard(stimulus, false);
    card.value = assignValue(card.image_name, jsPsych);
    card.value_label = formatValue(card.value);
    card.origin_trial_number = trialNumber;
    return card;
}

function materializeRepeatedCard(repeatEntry) {
    const stimulus = {
        image_name: repeatEntry.image_name,
        things_file_path: repeatEntry.things_file_path || "",
        things_memorability: repeatEntry.things_memorability,
        things_category: repeatEntry.things_category || "",
        memorability_percentile: repeatEntry.memorability_percentile || null
    };
    const card = materializeCard(stimulus, true);
    card.image_path = repeatEntry.image_path;
    card.value = repeatEntry.value;
    card.value_label = formatValue(card.value);
    card.origin_trial_number = repeatEntry.origin_trial_number;
    return card;
}

function assignValue(imageName, jsPsych) {
    if (TASK_STATE.imageValueMap.has(imageName)) {
        return TASK_STATE.imageValueMap.get(imageName);
    }
    const value = jsPsych.randomization.sampleWithoutReplacement(params.possible_values, 1)[0];
    TASK_STATE.imageValueMap.set(imageName, value);
    return value;
}

function buildBlankCanvasTrial(duration) {
    return {
        type: jsPsychCanvasKeyboardResponse,
        canvas_size: [850, 1200],
        choices: "NO_KEYS",
        trial_duration: duration,
        stimulus: function (canvas) {
            const ctx = canvas.getContext("2d");
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
    };
}

function drawChoiceDisplay(ctx, trial) {
    const dims = getCardLayout(ctx.canvas);
    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
    drawCard(ctx, dims.leftX, dims.cardY, dims.cardWidth, dims.cardHeight, IMAGE_CACHE[trial.left.image_path]);
    drawCard(ctx, dims.rightX, dims.cardY, dims.cardWidth, dims.cardHeight, IMAGE_CACHE[trial.right.image_path]);
}

function drawFeedbackDisplay(ctx, trial, lastData) {
    const dims = getCardLayout(ctx.canvas);
    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);

    if (!lastData.response) {
        ctx.fillStyle = "#c93b32";
        ctx.font = "bold 48px Inter";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("Too Slow!", ctx.canvas.width / 2, ctx.canvas.height / 2);
        return;
    }

    const chosenSide = lastData.chosen_side;
    const chosenCard = trial[chosenSide];
    const unchosenSide = chosenSide === "left" ? "right" : "left";
    const unchosenCard = trial[unchosenSide];
    const chosenX = chosenSide === "left" ? dims.leftX : dims.rightX;
    const unchosenX = chosenSide === "left" ? dims.rightX : dims.leftX;

    const startTime = performance.now();

    function animate(now) {
        const elapsed = now - startTime;
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);

        drawCard(ctx, unchosenX, dims.cardY, dims.cardWidth, dims.cardHeight, IMAGE_CACHE[unchosenCard.image_path], null, false, 1, 0.45);

        if (elapsed < params.highlight_duration) {
            drawCard(ctx, chosenX, dims.cardY, dims.cardWidth, dims.cardHeight, IMAGE_CACHE[chosenCard.image_path], null, true);
        } else {
            const flipElapsed = elapsed - params.highlight_duration;
            const progress = Math.min(flipElapsed / params.flip_duration, 1);

            if (progress < 0.5) {
                drawCard(ctx, chosenX, dims.cardY, dims.cardWidth, dims.cardHeight, IMAGE_CACHE[chosenCard.image_path], null, true, Math.max(0.02, 1 - progress * 2));
            } else {
                drawCard(
                    ctx,
                    chosenX,
                    dims.cardY,
                    dims.cardWidth,
                    dims.cardHeight,
                    IMAGE_CACHE[chosenCard.image_path],
                    chosenCard.value_label,
                    true,
                    Math.max(0.02, (progress - 0.5) * 2)
                );
            }
        }

        if (elapsed < params.highlight_duration + params.flip_duration + params.revealed_duration) {
            requestAnimationFrame(animate);
        }
    }

    requestAnimationFrame(animate);
}

function getCardLayout(canvas) {
    const cardWidth = 380;
    const cardHeight = 540;
    const spacing = 80;
    const leftX = canvas.width / 2 - cardWidth - spacing / 2;
    const rightX = canvas.width / 2 + spacing / 2;
    const cardY = canvas.height / 2 - cardHeight / 2;
    return { cardWidth, cardHeight, leftX, rightX, cardY };
}

function drawCard(ctx, x, y, width, height, image, valueLabel = null, isSelected = false, hScale = 1, alpha = 1) {
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.translate(x + width / 2, y + height / 2);
    ctx.scale(hScale, 1);
    ctx.translate(-width / 2, -height / 2);

    ctx.fillStyle = "#ffffff";
    ctx.beginPath();
    ctx.roundRect(0, 0, width, height, 22);
    ctx.fill();

    ctx.strokeStyle = params.card_color;
    ctx.lineWidth = isSelected ? 12 : 10;
    if (isSelected) {
        ctx.shadowBlur = 18;
        ctx.shadowColor = params.highlight_color;
    }
    ctx.stroke();
    ctx.shadowBlur = 0;

    const innerGradient = ctx.createLinearGradient(0, 0, width, height);
    innerGradient.addColorStop(0, "#f3f4f5");
    innerGradient.addColorStop(1, "#e5e7ea");
    ctx.fillStyle = innerGradient;
    ctx.beginPath();
    ctx.roundRect(24, 24, width - 48, height - 48, 16);
    ctx.fill();

    if (image && image.complete) {
        const padding = 34;
        const maxW = width - padding * 2;
        const maxH = height - padding * 2;
        const scale = Math.min(maxW / image.naturalWidth, maxH / image.naturalHeight);
        const drawW = image.naturalWidth * scale;
        const drawH = image.naturalHeight * scale;
        ctx.drawImage(image, (width - drawW) / 2, (height - drawH) / 2, drawW, drawH);
    }

    if (valueLabel) {
        const boxW = 180;
        const boxH = 104;
        const boxX = (width - boxW) / 2;
        const boxY = (height - boxH) / 2;

        ctx.fillStyle = "rgba(255, 255, 255, 0.96)";
        ctx.strokeStyle = params.card_color;
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.roundRect(boxX, boxY, boxW, boxH, 14);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = "#111111";
        ctx.font = "bold 54px Inter";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(valueLabel, width / 2, height / 2 + 2);
    }

    ctx.restore();
}

function loadStimulusMetadata() {
    const rows = window.STIMULI_METADATA;
    if (!Array.isArray(rows) || rows.length === 0) {
        throw new Error("Stimulus metadata is missing. Make sure ../../stimuli/_stimuli_metadata.js is loaded.");
    }
    return rows;
}

function getRepeatSummary(jsPsych) {
    const repeatTrials = jsPsych.data.get().filterCustom((trial) => trial.is_choice_trial && trial.is_repeat_trial && trial.optimal_repeat_choice !== null).values();
    const nRepeatTrials = repeatTrials.length;
    const nOptimal = repeatTrials.filter((trial) => trial.optimal_repeat_choice).length;
    const optimalRate = nRepeatTrials > 0 ? nOptimal / nRepeatTrials : 0;
    return {
        nRepeatTrials,
        nOptimal,
        optimalRate,
        bonus: params.max_bonus * optimalRate
    };
}

function formatValue(value) {
    if (value === 1 || value === 1.0) {
        return "$1";
    }
    return `${Math.round(value * 100)}¢`;
}
