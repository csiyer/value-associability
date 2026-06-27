function renderSequenceSimulation() {
    const plan = EpisodicChoiceSequence.buildSequencePlan(params, window.STIMULI_METADATA);
    const summary = EpisodicChoiceSequence.summarizePlan(plan);
    const summaryNode = document.getElementById("summary");
    const tableBody = document.getElementById("trial-table");

    const delaysByBin = { high: [], mid: [], low: [] };
    plan.trials.forEach((trial) => {
        if (trial.trial_type === "old") delaysByBin[trial.memorability_bin].push(trial.delay);
    });
    summary.mean_delay_by_bin = Object.fromEntries(
        Object.entries(delaysByBin).map(([bin, delays]) => [
            bin,
            delays.length ? +(delays.reduce((a, b) => a + b, 0) / delays.length).toFixed(3) : null,
        ])
    );

    summaryNode.textContent = JSON.stringify(summary, null, 2);
    tableBody.innerHTML = "";

    plan.trials.slice(0, 30).forEach((trial) => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${trial.trial_number}</td>
            <td>${trial.block_index}</td>
            <td>${trial.memorability_bin}</td>
            <td>${trial.trial_type}</td>
            <td>${trial.source_trial_number ?? ""}</td>
            <td>${trial.delay ?? ""}</td>
            <td>${trial.old_side ?? ""}</td>
            <td>${trial.shared_value ?? ""}</td>
            <td>${trial.lure_value ?? ""}</td>
        `;
        tableBody.appendChild(row);
    });
}

document.getElementById("rerun").addEventListener("click", renderSequenceSimulation);
renderSequenceSimulation();
