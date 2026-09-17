%% load Duncan's data

dirPath = '/Users/Daniel/Documents/MATLAB/DATA/Duncan_decorative_mats/raw_by_subject/';

dirContent = dir(dirPath);
count = 0;
dataMaster = [];
for i = 1:length(dirContent)
    [~,~,ext] = fileparts(dirContent(i).name);
    if strcmp(ext,'.csv')
        count = count + 1;
        dataTemp = csvread(fullfile(dirPath,dirContent(i).name));
        dataTemp(:,end+1) = count;
        dataMaster = [dataMaster; dataTemp];
    end
    clear dataTemp
end
% Col1: Value of the old object (0, 0.2, 0.4, 0.6, 0.8 or 1)
% Col2: chose old=1, did not choose old = 0
% Col3: Reaction time in seconds
% Col4: Familiarity (1 = shown on the same background as first time, 0 = shown on a different background than first time item is seen)
% Col5: Delay (continuous, number of trials since old item seen for the first time)
% Col6: Encoding scene new (1 = background when the old item was seen for the first time was new i.e. background was never seen before encoding of the old item, 0 = the background when the old item was seen for the first time was old and had been experience before then)


%% pre-process Duncan's data


% center value about zero and scale to range 1
dataMaster(:,1) = dataMaster(:,1) ./ range(dataMaster(:,1));
dataMaster(:,1) = dataMaster(:,1) - 0.5;

subjSet = unique(dataMaster(:,end));
nSubj = length(subjSet);

% compute number of "Error" trials
bitErr = (dataMaster(:,1) < 0 & dataMaster(:,2) == 1) | ...
    (dataMaster(:,1) > 0 & dataMaster(:,2) == 0);
disp(sprintf('There are %d (%0.1f prct) error trials out of %d total trials',...
    sum(bitErr),100*sum(bitErr)/size(dataMaster,1),size(dataMaster,1)));


%% set fit options

% As described in book "Bayesian Brain: Probabilistic Approaches to Neural 
% Coding" edited by Kenji Doya, Shin Ishii, Alexandre Pouget and Rajesh PN.,
% Rao, Chapter 10, "The speed and accuracy of a simple perceptual decision:
% A mathematical primer", the probability of choosing the
% positive/rightward direction and the decision time can be expressed as a 
% function of the motion strength (coherence),
%
%   p = 1 / (1 + exp(-2 * KC * A)) + prBias
%   t = A / KC * tanh(KC * A) + t_nd
%   where
%       KC = k * (coh + cohBias) + uBias,
%       k = fitted parameter,
%       A = flat bound height,
%       coh = signed coherence,
%       cohBias = motion strength bias or coherence bias,
%       uBias = drift force bias,
%       t_nd = non-decision time,
%       prBias = vertical probability bias.

% To apply Flat Bound fit, first create Flat Bound fit options,
fitOptions = flatBoundFitOptions6;
fitOptions.isPlotErrorBar = false;

% fit errors
% By default, fitting will be performed on condensed data without error RT.
% To fit data with error RT, set 'isFitErrorRT' & 'isPlotErrorRT' field to 
% true. User can also supply fminsearch options by setting fminsearchOptions
% field. To plot the fitting result, call the designed Flat Bound fit 
% function,

fitOptions.isFitErrorRT = true;
fitOptions.isPlotErrorRT = true;

% This options contains all the necessary fields to supply raw fitting
% data, fitting and plot options. As shown, 'fitOptions' contains a field 
% 'thetaKey' to identify the key type of each theta value, which is 
%
% 'kappa','A','tndr','tndl','uBias','cohBias','prBias','kappaBias_S','cohBias_S','ABias_S','tnd_S'
%
% To fit the data using both rightward- and leftward- non-decision time, 
% the 'theta' field can be set as

% fitOptions.theta = [0.457*sqrt(1E3),25/sqrt(1E3), 0.3,0.35, NaN,NaN,NaN];

% fitOptions.theta = [0.457*sqrt(1E3),25/sqrt(1E3), 0.3,0.35, 0,0,0];

% fitOptions.theta = [0.457*sqrt(1E3),25/sqrt(1E3), 0.30,0.35, 0,0,0,NaN,NaN];

% fitOptions.theta = [1.6,0.7, 0.3,0.35, 0,NaN,NaN,0,0];
% fitOptions.theta = [1.6,0.7, 0.3,0.35, NaN, NaN,NaN,0,NaN];

fitOptions.theta = [1.6,0.7, 0.3,0.35, NaN, 0,NaN,0,NaN,NaN,NaN]; % full model

% Please note that any theta parameter that is set to NaN, means that this
% theta parameter is not fitted. In the above case, only 'kappa', 'A',
% 'tndr' and 'tndl' are fitted. 'kappa' & 'A' values are required for all
% fitting.
%
% By default, Flat Bound fit will exclude data if the number of choice is
% less than 'minorRTCriteria' since the variance is not accountable. The
% default 'minorRTCriteria' is 10. If user choose not to reject minor RT,
% 'isRejectMinorRT' field can be set to false.


%% use all subjects as one subject

data = dataMaster(:,1:4);

% fit
[thetaFit,err,exitflag,output,fitOptions] = flatBoundFit6(data,fitOptions);

% plot
fh3 = flatBoundFitPlot6(thetaFit,fitOptions);


%% process each subject separately

% instantiate
thetaFitAll = [];
errAll = [];

% loop through each subject
for i = 1:nSubj
    
    disp(sprintf('Processing file %d',i));
    
    % subset to single subject, keeping only first three rows of data
    data = dataMaster(dataMaster(:,end) == subjSet(i),1:4);

    [thetaFit,err,exitflag,output,fitOptions] = flatBoundFit6(data,fitOptions);
%   thetaFit = fitted theta value vector,
%   err = the value of the objective function of fminsearch,
%   exitflat = the exit condition of fminsearch,
%   output = standard output structure of fminsearch,
%   fitOptions = updated fit options with condensed data.
    
    % plot it
    fh3 = flatBoundFitPlot6(thetaFit,fitOptions);
    title(sprintf('Subject %d, err %0.2f',i,err));
    
    % collect fit data
    thetaFitAll(i,:) = thetaFit;
    errAll(i,:) = err;
    
end

%% clean up results

% certain subjects have wierd data
subj2Elim = [
    3
    4
    7
    8
    10
    14 % step function psycho around +0.3
    16 % poor range in psycho (P = 0.25 to 0.6), inverted chrono
    17
    20 % high error, flat psycho, flat chrono
    23
    ];

% certain subjects have wierd data
subj2Elim = [
    3
    6
    7
    8
    10
    12
    16
    20
    21
    24
    ];

% certain subjects have wierd data
subj2Elim = [
    3
    4
    6
    7
    8
    10
    12
    16
    18
    20
    21
    23
    24
    ];

disp('Mean and SEM across indiv subjects with outliers exluded')
foo = thetaFitAll;
foo(subj2Elim,:) = [];
thetaAll_mean = mean(foo)
thetaAll_sem = std(foo) / sqrt(size(foo,1))
clear foo

%% eliminate bad subjects from the master set and rerun

data = dataMaster(~ismember(dataMaster(:,end),subj2Elim),1:4);

% fit
[thetaFit,err,exitflag,output,fitOptions] = flatBoundFit(data,fitOptions);

% plot
fh3 = flatBoundFitPlot(thetaFit,fitOptions);



%% Plotting


fh3 = flatBoundFitPlot(thetaFit,fitOptions);

% Both FLATBOUNDFIT & FLATBOUNDFitPLOT function support the typical Matlab 
% way to change options field value. For example, to plot without the error 
% bar, the plot function can be called as,

% fh4 = flatBoundFitPlot(thetaFit,fitOptions,'isPlotErrorBar',false);

% To fit using combined reaction time, simply set the fitting parameter 
% 'theta' field to
%
%   [0.457*sqrt(1E3),25/sqrt(1E3), 0.3,NaN, NaN,NaN,NaN].
%
% and then call the fitting again. 'isFitErrorRT' & 'isPlotErrorRT' fields
% are only available to fitting using both righward- & leftward- reaction
% times. 'isFitCombinedRT' & 'isPlotCombinedRT' fields are used by internal 
% functions to indicate the fitting type. User should not set them.
%
% If fitting using Logit derived coherence bias, set 'ldcb'. For more
% options to fit and explore the Flat Bound fit function, please see also
% FLATBOUNDFIT, FLATBOUNDFITOPTIONS and FLATBOUNDFITPLOT.

