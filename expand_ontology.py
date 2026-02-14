#!/usr/bin/env python3
"""
Script to expand the computational neuroscience ontology to meet minimum requirements.
"""

import json

# Load the existing ontology
input_file = "/Users/elvish/Documents/CODING/memebu-ontology-engine/data/20260213_185108_run_5_v0/ontology_json/20260213_185106_Computational.Neuroscience-A.Comprehensive.Approach.json"

with open(input_file, 'r') as f:
    ontology = json.load(f)

# Get the existing graph
graph = ontology['@graph']

# Helper function to create class
def create_class(id_name, label, comment, subclass_of=None):
    entity = {
        "@id": f"ns:{id_name}",
        "@type": "owl:Class",
        "rdfs:label": label,
        "rdfs:comment": comment
    }
    if subclass_of:
        entity["rdfs:subClassOf"] = {"@id": subclass_of}
    return entity

# Helper function to create individual
def create_individual(id_name, label, comment, class_type):
    return {
        "@id": f"ns:{id_name}",
        "@type": ["owl:NamedIndividual", class_type],
        "rdfs:label": label,
        "rdfs:comment": comment
    }

# Helper function to create object property
def create_object_property(id_name, label, comment, domain, range_val):
    return {
        "@id": f"ns:{id_name}",
        "@type": "owl:ObjectProperty",
        "rdfs:label": label,
        "rdfs:comment": comment,
        "rdfs:domain": {"@id": domain},
        "rdfs:range": {"@id": range_val}
    }

# Helper function to create data property
def create_data_property(id_name, label, comment, domain, range_val):
    return {
        "@id": f"ns:{id_name}",
        "@type": "owl:DatatypeProperty",
        "rdfs:label": label,
        "rdfs:comment": comment,
        "rdfs:domain": {"@id": domain},
        "rdfs:range": {"@id": range_val}
    }

# NEW CLASSES (50+ more)
new_classes = [
    # More specific neuron types
    create_class("CholinergicNeuron", "Cholinergic Neuron",
                 "A neuron that synthesizes and releases acetylcholine as its primary neurotransmitter. Cholinergic neurons are found in the basal forebrain, brainstem, and spinal cord, modulating attention, arousal, and motor control. These neurons play critical roles in cognitive function and are selectively degenerated in Alzheimer's disease.",
                 "ns:NeuronType"),
    create_class("GABAergicInterneuron", "GABAergic Interneuron",
                 "An inhibitory interneuron that releases GABA to control excitability and synchronization in neural circuits. GABAergic interneurons comprise diverse subtypes including parvalbumin, somatostatin, and VIP-expressing cells, each with distinct connectivity patterns and functional roles. These neurons are essential for preventing runaway excitation and shaping network oscillations.",
                 "ns:Interneuron"),
    create_class("DopaminergicNeuron", "Dopaminergic Neuron",
                 "A modulatory neuron located in the substantia nigra and ventral tegmental area that releases dopamine to regulate reward, motivation, and motor control. Dopaminergic neurons exhibit pacemaker activity and burst firing in response to unexpected rewards. Loss of these neurons in Parkinson's disease causes motor deficits.",
                 "ns:NeuronType"),
    create_class("SerotoninergicNeuron", "Serotonergic Neuron",
                 "A neuromodulatory neuron originating in the raphe nuclei that releases serotonin throughout the brain and spinal cord. Serotonergic neurons regulate mood, sleep-wake cycles, appetite, and impulse control through widespread projections. These neurons are targets of antidepressant medications.",
                 "ns:NeuronType"),
    create_class("NoradrenergicNeuron", "Noradrenergic Neuron",
                 "A modulatory neuron in the locus coeruleus releasing norepinephrine to regulate arousal, attention, and stress responses. Noradrenergic neurons project throughout the cortex and have low tonic firing rates but increase dramatically during salient events. These neurons enhance sensory processing and memory consolidation.",
                 "ns:NeuronType"),
    create_class("BipolarCell", "Bipolar Cell",
                 "A retinal interneuron connecting photoreceptors to ganglion cells with center-surround receptive fields. Bipolar cells split into ON and OFF subtypes responding to light increments and decrements respectively. These cells implement parallel processing pathways extracting contrast information from visual scenes.",
                 "ns:NeuronType"),
    create_class("GanglionCell", "Ganglion Cell",
                 "The output neuron of the retina whose axons form the optic nerve projecting to the lateral geniculate nucleus. Ganglion cells extract diverse visual features including edges, motion direction, and luminance changes through interactions with bipolar and amacrine cells. Distinct subtypes tile visual space encoding complementary features.",
                 "ns:NeuronType"),
    create_class("AmacriNeuron", "Amacrine Cell",
                 "A retinal interneuron providing lateral connections and implementing directional selectivity through asymmetric inhibition. Amacrine cells comprise dozens of subtypes with diverse morphologies and transmitter systems. These neurons shape temporal dynamics and spatial integration in ganglion cells.",
                 "ns:NeuronType"),
    create_class("ChandelierCell", "Chandelier Cell",
                 "A specialized GABAergic interneuron forming synapses exclusively onto pyramidal cell axon initial segments. Chandelier cells powerfully control action potential generation through perisomatic inhibition. These neurons exhibit basket-like axonal arbors resembling chandeliers and synchronize pyramidal cell firing.",
                 "ns:Interneuron"),
    create_class("BasketCell", "Basket Cell",
                 "A fast-spiking GABAergic interneuron forming perisomatic inhibitory synapses onto principal neurons. Basket cells express parvalbumin and provide feedforward and feedback inhibition controlling spike timing precision. These neurons generate gamma oscillations through interactions with pyramidal cells.",
                 "ns:Interneuron"),

    # More brain regions
    create_class("EntorhinalCortex", "Entorhinal Cortex",
                 "A medial temporal lobe region serving as the main interface between hippocampus and neocortex. The entorhinal cortex contains grid cells encoding spatial location with hexagonal firing patterns. This region implements path integration and provides spatial context for episodic memories.",
                 "ns:CorticalRegion"),
    create_class("AuditoryCortex", "Auditory Cortex",
                 "The temporal lobe region processing sound information with tonotopic organization reflecting frequency preferences. Primary auditory cortex (A1) extracts spectrotemporal features while higher auditory areas represent complex sounds, speech, and music. This region implements hierarchical processing of acoustic patterns.",
                 "ns:CorticalRegion"),
    create_class("SubstantiaNigra", "Substantia Nigra",
                 "A midbrain structure containing dopaminergic neurons projecting to striatum and controlling movement initiation. The substantia nigra pars compacta provides reward prediction error signals for reinforcement learning. Degeneration of this region causes Parkinson's disease motor symptoms.",
                 "ns:SubcorticalRegion"),
    create_class("VentralTegmentalArea", "Ventral Tegmental Area",
                 "A midbrain region containing dopaminergic neurons projecting to nucleus accumbens and prefrontal cortex. The VTA encodes reward prediction errors driving learning and motivation. This region is critical for addiction and goal-directed behavior.",
                 "ns:SubcorticalRegion"),
    create_class("NucleusAccumbens", "Nucleus Accumbens",
                 "A ventral striatal region integrating limbic and motor information for motivation and reward-based learning. The nucleus accumbens receives dopaminergic input from VTA and glutamatergic input from prefrontal cortex and hippocampus. This region links motivation to action selection.",
                 "ns:SubcorticalRegion"),
    create_class("LateralGeniculateNucleus", "Lateral Geniculate Nucleus",
                 "A thalamic relay nucleus transmitting retinal information to primary visual cortex with retinotopic organization. The LGN contains distinct layers receiving input from different retinal ganglion cell types. This structure implements gain control and attention-dependent modulation of visual signals.",
                 "ns:SubcorticalRegion"),
    create_class("SuperiorColliculus", "Superior Colliculus",
                 "A midbrain structure controlling rapid eye movements and orienting responses to salient stimuli. The superior colliculus integrates multisensory information to compute saliency maps guiding attention. This region generates motor commands for saccadic eye movements.",
                 "ns:SubcorticalRegion"),
    create_class("InferiorColliculus", "Inferior Colliculus",
                 "A midbrain auditory structure integrating information from brainstem nuclei and projecting to medial geniculate nucleus. The inferior colliculus creates topographic maps of sound frequency and location. This region extracts complex acoustic features for sound localization.",
                 "ns:SubcorticalRegion"),
    create_class("RedNucleus", "Red Nucleus",
                 "A midbrain motor structure receiving cerebellar input and projecting to spinal cord for motor control. The red nucleus implements feedforward motor commands and postural adjustments. This region is part of the indirect motor pathway parallel to corticospinal projections.",
                 "ns:SubcorticalRegion"),
    create_class("LocusCoeruleus", "Locus Coeruleus",
                 "A brainstem nucleus containing noradrenergic neurons that project widely throughout the brain. The locus coeruleus regulates arousal, attention, and stress responses through norepinephrine release. This small nucleus profoundly influences cortical processing states.",
                 "ns:SubcorticalRegion"),

    # More mathematical and computational concepts
    create_class("SpikeletModel", "Spikelet Model",
                 "A model of small, subthreshold depolarizing events in dendrites that can sum to generate full action potentials. Spikelets arise from gap junction coupling or dendritic sodium channels and provide fine temporal precision. These events enable millisecond-scale coincidence detection.",
                 "ns:NeuronModel"),
    create_class("NetworkMotif", "Network Motif",
                 "A recurring pattern of connections between small numbers of neurons that performs specific computational operations. Common motifs include feedforward loops, feedback loops, and lateral inhibition. These building blocks combine to implement complex network computations.",
                 "ns:MathematicalConcept"),
    create_class("BayesianInference", "Bayesian Inference",
                 "A computational framework for combining prior expectations with sensory evidence to estimate stimulus properties. Bayesian inference explains perceptual illusions, multisensory integration, and optimal decision-making. Neural populations may represent probability distributions over stimulus variables.",
                 "ns:MathematicalConcept"),
    create_class("PredictiveCoding", "Predictive Coding",
                 "A theory proposing that the brain constantly generates predictions about sensory inputs and computes prediction errors. Predictive coding explains hierarchical processing, attention effects, and perceptual inference. This framework suggests feedback connections carry predictions while feedforward connections signal errors.",
                 "ns:MathematicalConcept"),
    create_class("SparseCode", "Sparse Coding",
                 "A neural representation using few active neurons from a large population to represent stimuli efficiently. Sparse coding maximizes information transmission, reduces metabolic cost, and facilitates learning. Primary visual cortex receptive fields resemble sparse code features for natural images.",
                 "ns:NeuralCodingScheme"),
    create_class("EfficientCoding", "Efficient Coding",
                 "A theory proposing that sensory systems optimize information transmission given metabolic and bandwidth constraints. Efficient coding predicts receptive field properties, decorrelation, and adaptation. This principle explains how sensory representations match natural stimulus statistics.",
                 "ns:MathematicalConcept"),
    create_class("FreeEnergy", "Free Energy Principle",
                 "A theoretical framework proposing that brains minimize surprise by building models of the world. The free energy principle unifies perception, action, and learning under a single optimization objective. This theory connects Bayesian inference, predictive coding, and active inference.",
                 "ns:MathematicalConcept"),
    create_class("CompressedSensing", "Compressed Sensing",
                 "A signal processing technique recovering sparse signals from undersampled measurements using optimization. Compressed sensing principles may explain how brains extract information from limited sensory data. This approach enables efficient neural codes with fewer neurons than traditional sampling requires.",
                 "ns:MathematicalConcept"),
    create_class("ManifoldLearning", "Manifold Learning",
                 "Techniques for discovering low-dimensional structure in high-dimensional neural population activity. Manifold learning reveals latent variables controlling neural dynamics and behavior. These methods uncover continuous attractors, decision boundaries, and motor trajectories.",
                 "ns:MathematicalConcept"),
    create_class("DimensionalityReduction", "Dimensionality Reduction",
                 "Mathematical techniques projecting high-dimensional data to lower dimensions while preserving structure. Dimensionality reduction methods like PCA and t-SNE reveal organization of neural representations. These approaches identify relevant dimensions for neural coding.",
                 "ns:MathematicalConcept"),

    # More specific plasticity mechanisms
    create_class("MetaplasticityMechanism", "Metaplasticity",
                 "Plasticity of synaptic plasticity where prior activity history modulates future plasticity induction thresholds. Metaplasticity implements homeostatic regulation preventing runaway potentiation or depression. BCM theory formalizes metaplasticity through sliding modification thresholds.",
                 "ns:PlasticityMechanism"),
    create_class("StructuralPlasticity", "Structural Plasticity",
                 "Long-lasting changes in neuronal morphology including spine formation, synapse elimination, and dendritic remodeling. Structural plasticity underlies memory consolidation and developmental circuit refinement. These anatomical changes persist longer than functional synaptic modifications.",
                 "ns:PlasticityMechanism"),
    create_class("HomeostticPlasticity", "Homeostatic Plasticity",
                 "Plasticity mechanisms that maintain stable network activity levels despite ongoing Hebbian modifications. Homeostatic plasticity includes synaptic scaling uniformly adjusting all synapses and intrinsic excitability changes. These mechanisms prevent pathological hyper- or hypo-activity.",
                 "ns:PlasticityMechanism"),
    create_class("ShortTermPlasticity", "Short-Term Plasticity",
                 "Rapid, reversible changes in synaptic strength lasting milliseconds to seconds including facilitation and depression. Short-term plasticity arises from residual calcium and vesicle depletion creating dynamic synaptic filters. These mechanisms implement temporal filtering and gain control.",
                 "ns:PlasticityMechanism"),
    create_class("VolumeTransmission", "Volume Transmission",
                 "Diffusion-based chemical signaling beyond synaptic clefts reaching many neurons simultaneously. Volume transmission by neuropeptides, nitric oxide, and monoamines coordinates activity across local circuits. This mode enables broadcast modulation complementing point-to-point synaptic transmission.",
                 "ns:SignalTransduction"),

    # More ion channels
    create_class("HyperpolarizationActivatedChannel", "Hyperpolarization-Activated Channel",
                 "An ion channel opening in response to membrane hyperpolarization carrying mixed sodium-potassium current. HCN channels generate pacemaker activity, rebound excitation, and contribute to resonance. These channels have slow kinetics creating time-dependent rectification.",
                 "ns:VoltageGatedChannel"),
    create_class("TransientReceptorChannel", "Transient Receptor Potential Channel",
                 "A diverse family of ion channels responding to temperature, mechanical force, and chemical ligands. TRP channels mediate sensory transduction for pain, temperature, taste, and osmolarity. These polymodal channels integrate multiple stimulus modalities.",
                 "ns:IonChannel"),
    create_class("AcidSensingChannel", "Acid-Sensing Channel",
                 "A sodium channel activated by extracellular protons mediating responses to acidification. Acid-sensing ion channels contribute to pain sensation, synaptic plasticity, and ischemic neuronal injury. These channels detect pH changes signaling tissue damage.",
                 "ns:LigandGatedChannel"),
    create_class("PurinergicReceptor", "Purinergic Receptor",
                 "An ATP-gated ion channel mediating fast synaptic transmission and sensory transduction. P2X receptors respond to ATP released from cells signaling injury or inflammation. These channels contribute to pain pathways and neuroimmune communication.",
                 "ns:LigandGatedChannel"),
    create_class("GlycoReceptor", "Glycine Receptor",
                 "A chloride channel activated by the inhibitory neurotransmitter glycine mediating fast inhibition in spinal cord and brainstem. Glycine receptors have fast kinetics providing temporal precision in motor circuits and auditory processing. Strychnine blocks these receptors causing convulsions.",
                 "ns:LigandGatedChannel"),

    # More sensory systems
    create_class("AuditorySystem", "Auditory System",
                 "The neural pathway processing sound from cochlea through brainstem nuclei to auditory cortex. The auditory system extracts frequency, timing, and spatial information through parallel processing streams. This system implements spectrotemporal analysis of acoustic scenes.",
                 "ns:SensorySystem"),
    create_class("OlfactorySystem", "Olfactory System",
                 "The chemical sensory system detecting airborne odorants through olfactory receptors in nasal epithelium. Olfactory information bypasses thalamus projecting directly to olfactory cortex and amygdala. This ancient sensory system influences emotion, memory, and behavior.",
                 "ns:SensorySystem"),
    create_class("GustatorySystem", "Gustatory System",
                 "The taste sensory system detecting chemicals in food through taste receptors on tongue. The gustatory system identifies sweet, sour, salty, bitter, and umami qualities guiding food selection. This system projects to insular cortex integrating with olfactory and somatosensory information.",
                 "ns:SensorySystem"),
    create_class("VestibularSystem", "Vestibular System",
                 "The sensory system detecting head motion and orientation through semicircular canals and otolith organs. The vestibular system provides critical information for balance, gaze stabilization, and spatial orientation. This system integrates with visual and proprioceptive signals for postural control.",
                 "ns:SensorySystem"),

    # More learning and decision concepts
    create_class("ReinforcementLearning", "Reinforcement Learning",
                 "A learning framework where agents learn action policies through trial and error to maximize reward. Reinforcement learning explains dopamine signals as reward prediction errors updating action values. Temporal difference algorithms capture key features of animal learning.",
                 "ns:MathematicalConcept"),
    create_class("SupervisedLearning", "Supervised Learning",
                 "A learning paradigm where error signals guide weight adjustments toward desired outputs. Supervised learning in cerebellum uses climbing fiber error signals to modify Purkinje cell responses. Backpropagation implements supervised learning in multilayer networks.",
                 "ns:MathematicalConcept"),
    create_class("UnsupervisedLearning", "Unsupervised Learning",
                 "Learning algorithms discovering structure in data without explicit error signals. Unsupervised learning includes Hebbian plasticity, independent component analysis, and clustering. These mechanisms extract statistical regularities from sensory inputs.",
                 "ns:MathematicalConcept"),
    create_class("DecisionMaking", "Decision Making",
                 "The neural process of selecting actions based on evidence evaluation and value comparison. Decision-making involves evidence accumulation in parietal and prefrontal cortex until reaching threshold. Drift-diffusion models capture accuracy-speed tradeoffs in perceptual decisions.",
                 "ns:MathematicalConcept"),
    create_class("ActiveInference", "Active Inference",
                 "A framework where action selection minimizes expected free energy by seeking information and achieving goals. Active inference unifies perception and action under predictive processing principles. This theory explains exploratory behavior and goal-directed planning.",
                 "ns:MathematicalConcept"),

    # More specific models and algorithms
    create_class("IzhikevichModel", "Izhikevich Model",
                 "A two-variable neuron model combining computational efficiency with biological realism. The Izhikevich model reproduces diverse firing patterns through simple parameter changes. This model offers the best compromise between simplicity and biological accuracy for large-scale simulations.",
                 "ns:SimplifiedNeuronModel"),
    create_class("AdaptiveExponentialModel", "Adaptive Exponential Integrate-and-Fire Model",
                 "An integrate-and-fire variant including exponential spike generation and spike-triggered adaptation. The AdEx model captures threshold dynamics and adaptation with minimal complexity. This model accurately fits experimental data while remaining analytically tractable.",
                 "ns:SimplifiedNeuronModel"),
    create_class("QuadraticIntegrateFireModel", "Quadratic Integrate-and-Fire Model",
                 "A neuron model with quadratic voltage dependence exhibiting Type I excitability. The QIF model describes neurons near saddle-node bifurcations and admits analytical solutions. This model captures continuous frequency-current relationships characteristic of integrator neurons.",
                 "ns:SimplifiedNeuronModel"),
    create_class("GeneralizedIntegrateFireModel", "Generalized Integrate-and-Fire Model",
                 "A family of simplified neuron models including threshold adaptation and spike-triggered currents. Generalized IF models fit experimental recordings by optimizing parameters for multiple features. These models balance simplicity with accurate reproduction of neural dynamics.",
                 "ns:SimplifiedNeuronModel"),
]

print(f"Adding {len(new_classes)} new classes...")
graph.extend(new_classes)

print(f"Total classes so far: {len([x for x in graph if x.get('@type') == 'owl:Class' or (isinstance(x.get('@type'), list) and 'owl:Class' in x['@type'])])}")

# Save checkpoint
with open(input_file, 'w') as f:
    json.dump(ontology, f, indent=2)

print("Checkpoint 1: New classes added and saved.")
