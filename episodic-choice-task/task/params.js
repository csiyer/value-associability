const params = {
    experiment_id: "episodic_choice_v1",

    n_trials: 60,
    old_trial_pct: 0.6,
    min_trials_ago: 9,
    max_trials_ago: 30,
    possible_values: [0, 0.2, 0.4, 0.6, 0.8, 1.0],

    choice_duration: 2000,
    highlight_duration: 500,
    flip_duration: 500,
    revealed_duration: 1000,
    too_slow_duration: 1200,
    iti: 800,

    background_color: "#ececec",
    text_color: "#333333",
    card_color: "#8c9299",
    highlight_color: "#cfd4da",

    completion_time: 6,
    base_pay: 2,
    max_bonus: 2,
    data_pipe_id: "PLACEHOLDER",
    prolific_completion_code: "PLACEHOLDER",

    consent_pdf: "https://csiyer.github.io/files/online_consent_form.pdf",
    stimuli_dir: "../../stimuli",
};

params.instruction_pages = [
    `<div class="instruction-container" style="max-width: 920px;">
        <h2>Consent Form</h2>
        <p>Please review the consent form below. Feel free to download a copy for your records.</p>
        <iframe src="${params.consent_pdf}" width="100%" height="600" style="border: 1px solid #e8e8e8; border-radius: 10px; margin-top: 10px;"></iframe>
        <p style="margin-top: 18px;">By clicking "Next," you confirm that you have read the form and voluntarily agree to participate.</p>
    </div>`,
    `<div class="instruction-container">
        <h2>How To Play</h2>
        <p>On each trial, you will see two cards. These cards are paired with random rewards between $0 and $1.</p>
        <div class="instruction-card-row">
            <div class="mini-card"></div>
            <div class="mini-card"></div>
        </div>
        <p>Pick a card with the <strong>left and right arrow keys</strong>. When you pick a card it will flip over to reveal its value. Your goal is to maximize your total rewards.</p>
    </div>`,
    `<div class="instruction-container">
        <h2>Repeated Cards</h2>
        <p>On some trials, you will see a card you have seen before. <strong>Cards will always be worth the same amount they were before.</strong> So, on these trials, you can use your memory to decide if the card is worth picking or not.</p>
        <div class="repeat-demo">
            <div class="repeat-demo-block">
                <div class="repeat-demo-label">Earlier</div>
                <div class="mini-card revealed"></div>
                <div class="repeat-demo-value">80¢</div>
            </div>
            <div class="instruction-arrow">...</div>
            <div class="repeat-demo-block">
                <div class="repeat-demo-label">Later</div>
                <div class="mini-card"></div>
                <div class="repeat-demo-value">same value</div>
            </div>
        </div>
    </div>`,
    `<div class="instruction-container">
        <h2>Summary</h2>
        <ul>
            <li>Pick cards with the left and right arrow keys to receive rewards.</li>
            <li>Remember the value of cards so that if they appear again, you can decide to pick them if they have high values.</li>
        </ul>
        <p>Press "Next" to begin the experiment!</p>
    </div>`
];

window.params = params;
