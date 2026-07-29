# ==============================================================================
# Chapter 3 — Core Concepts
# ==============================================================================

## ------------------------------------------------------------------------------
## 3.2 What is Architecture in the Context of the TOGAF Standard
## ------------------------------------------------------------------------------

```yaml
id: ARC-0001

name: Architecture

category: Core Concept

source:
  chapter: 3
  section: 3.2

definition:
  - Fundamental concepts or properties of a system embodied in its elements, relationships, and the principles of its design and evolution.
  - Structure of components, their interrelationships, and the principles and guidelines governing their design and evolution over time.

applies_to:
  - Enterprise
  - Business
  - Data
  - Application
  - Technology

contains:
  - Components
  - Relationships
  - Principles
  - Guidelines

describes:
  - System

characteristics:
  - Structured
  - Governed
  - Evolves
  - Principle-driven

rules:
  - Architecture describes a system.
  - Architecture contains components.
  - Components have relationships.
  - Principles govern architecture.
  - Architecture evolves over time.

validation:
  - System exists.
  - Components defined.
  - Relationships defined.
  - Principles defined.

related:
  - System
  - Component
  - Relationship
  - Principle
  - Guideline
```

---

## ------------------------------------------------------------------------------
## 3.3 What Kind of Architecture Does the TOGAF Standard Deal With?
## ------------------------------------------------------------------------------

```yaml
id: ARC-0002

name: Architecture Domains

category: Core Concept

source:
  chapter: 3
  section: 3.3

description:
  TOGAF defines four architecture domains as subsets of Enterprise Architecture.
  These domains together describe the enterprise from complementary perspectives.

domains:

  Business:
    purpose:
      - Business strategy
      - Governance
      - Organization
      - Key business processes

    produces:
      - Business models
      - Business capabilities
      - Business processes
      - Organization structure

  Data:
    purpose:
      - Logical data assets
      - Physical data assets
      - Data management resources

    produces:
      - Data models
      - Data entities
      - Data resources

  Application:
    purpose:
      - Application portfolio
      - Application interactions
      - Relationship to business processes

    produces:
      - Application models
      - Interfaces
      - Application interactions

  Technology:
    purpose:
      - Digital architecture
      - Software infrastructure
      - Hardware infrastructure
      - Technology standards
      - Infrastructure capabilities

    includes:
      - Cloud services
      - Middleware
      - Networks
      - Communications
      - Processing
      - Internet of Things
      - Social media infrastructure
      - IT infrastructure
      - Technology standards

derived_domains:
  - Information Architecture
  - Risk Architecture
  - Security Architecture
  - Digital Architecture

relationships:

  Enterprise Architecture:
    consists_of:
      - Business Architecture
      - Data Architecture
      - Application Architecture
      - Technology Architecture

  Business Architecture:
    influences:
      - Data Architecture
      - Application Architecture
      - Technology Architecture

  Data Architecture:
    supports:
      - Business Architecture
      - Application Architecture

  Application Architecture:
    supports:
      - Business Processes

  Technology Architecture:
    supports:
      - Business Services
      - Data Services
      - Application Services

rules:
  - Enterprise Architecture shall include Business Architecture.
  - Enterprise Architecture shall include Data Architecture.
  - Enterprise Architecture shall include Application Architecture.
  - Enterprise Architecture shall include Technology Architecture.
  - Additional architecture domains may be created by combining views from the four core domains.

validation:
  - Business domain defined.
  - Data domain defined.
  - Application domain defined.
  - Technology domain defined.
  - Domain relationships established.

related:
  - Architecture
  - Enterprise
  - Business Architecture
  - Data Architecture
  - Application Architecture
  - Technology Architecture
  - Information Architecture
  - Risk Architecture
  - Security Architecture
  - Digital Architecture
```

---

## ------------------------------------------------------------------------------
## 3.4 Architecture Development Method (ADM)
## ------------------------------------------------------------------------------

```yaml
id: ARC-0003

name: Architecture Development Method (ADM)

category: Core Concept

source:
  chapter: 3
  section: 3.4

definition:
  A tested and repeatable process for developing Enterprise Architectures.

purpose:
  - Establish an Architecture Capability
  - Develop architecture content
  - Plan transformation
  - Govern implementation
  - Manage architectural change

characteristics:
  - Iterative
  - Repeatable
  - Continuous
  - Architecture-driven
  - Business-driven

lifecycle:

  Preliminary:
    objective:
      - Establish Architecture Capability
      - Customize TOGAF
      - Define Architecture Principles

  Phase A:
    name: Architecture Vision
    objective:
      - Define scope
      - Identify stakeholders
      - Develop Architecture Vision
      - Obtain approval

  Phase B:
    name: Business Architecture
    objective:
      - Develop Business Architecture
      - Support agreed Architecture Vision

  Phase C:
    name: Information Systems Architectures
    objective:
      - Develop Data Architecture
      - Develop Application Architecture

  Phase D:
    name: Technology Architecture
    objective:
      - Develop Technology Architecture

  Phase E:
    name: Opportunities and Solutions
    objective:
      - Initial implementation planning
      - Identify delivery vehicles

  Phase F:
    name: Migration Planning
    objective:
      - Move from Baseline to Target Architecture
      - Produce Implementation and Migration Plan

  Phase G:
    name: Implementation Governance
    objective:
      - Govern implementation
      - Provide architectural oversight

  Phase H:
    name: Architecture Change Management
    objective:
      - Manage architecture change
      - Maintain architecture lifecycle

requirements_management:
  purpose:
    - Manage architecture requirements across all ADM phases

relationships:

  ADM:
    develops:
      - Business Architecture
      - Data Architecture
      - Application Architecture
      - Technology Architecture

  ADM:
    governs:
      - Implementation
      - Architecture Change

  ADM:
    produces:
      - Architecture Deliverables
      - Architecture Artifacts
      - Building Blocks

rules:
  - ADM is iterative.
  - Requirements Management spans all phases.
  - ADM supports continuous architecture development.
  - ADM should be adapted to enterprise needs.
  - ADM supports different architecture styles.
  - ADM does not require a fixed phase sequence.
  - ADM does not mandate a waterfall approach.

validation:
  - Architecture Capability established.
  - Architecture Vision approved.
  - All required architecture domains developed.
  - Migration Plan produced.
  - Governance established.
  - Change Management established.
  - Requirements managed throughout the lifecycle.

related:
  - Architecture
  - Enterprise Architecture
  - Business Architecture
  - Data Architecture
  - Application Architecture
  - Technology Architecture
  - Requirements Management
  - Architecture Principles
```

---

## ------------------------------------------------------------------------------
## 3.5 Enterprise Architecture Services
## ------------------------------------------------------------------------------

```yaml
id: ARC-0004

name: Enterprise Architecture Services

category: Core Concept

source:
  chapter: 3
  section: 3.5

definition:
  Enterprise Architecture activities are delivered through a service delivery model.
  Services are organized into categories that address specific enterprise needs
  independent of an organization's operating model.

purpose:
  - Deliver Enterprise Architecture capabilities as services
  - Support organizational change
  - Support decision-making
  - Apply ADM activities to business needs
  - Improve Enterprise Architecture capability

characteristics:
  - Service-oriented
  - Customer-focused
  - Reusable
  - Independent of operating model
  - Based on ADM activities

service_categories:

  Enterprise Support Services:
    objective:
      - Support strategic decision-making
      - Provide enterprise analysis
      - Answer enterprise-level questions

    timing:
      - Independent of projects

  Design Support Services:
    objective:
      - Support design decisions
      - Develop Minimum Viable Architectures (MVAs)
      - Perform design analysis

    timing:
      - After project funding
      - Waterfall projects
      - Agile projects

  Development Support Services:
    objective:
      - Support development decisions
      - Provide enterprise analysis during implementation

    timing:
      - During project development
      - Waterfall projects
      - Agile projects

  Requirements Elicitation and Understanding Services:
    objective:
      - Improve understanding of requirements
      - Identify real business needs
      - Increase business value

  Architecture Planning Services:
    objective:
      - Plan architecture projects
      - Support successful project execution

    timing:
      - Beginning of projects
      - Waterfall projects
      - Agile projects

  Enterprise Architecture Practice Development Support Services:
    objective:
      - Develop Enterprise Architecture practice
      - Manage Enterprise Architecture practice
      - Improve Enterprise Architecture Capability

relationships:

  Enterprise Architecture Services:
    uses:
      - Architecture Development Method (ADM)

  Enterprise Architecture Services:
    organized_into:
      - Enterprise Support Services
      - Design Support Services
      - Development Support Services
      - Requirements Elicitation and Understanding Services
      - Architecture Planning Services
      - Enterprise Architecture Practice Development Support Services

  service_categories:
    customer_centric:
      - Enterprise Support Services
      - Design Support Services
      - Development Support Services
      - Requirements Elicitation and Understanding Services

    architecture_practice:
      - Architecture Planning Services
      - Enterprise Architecture Practice Development Support Services

rules:
  - Enterprise Architecture activities should be delivered as services.
  - Services utilize appropriate ADM activities.
  - Services address enterprise needs independent of the operating model.
  - The first four service categories are customer-centric.
  - The remaining service categories focus on improving the Enterprise Architecture practice.

validation:
  - Service delivery model established.
  - Service categories defined.
  - ADM activities aligned with services.
  - Enterprise Architecture practice supported.
  - Customer services identified.

related:
  - Architecture Development Method
  - Enterprise Architecture
  - Enterprise Architecture Capability
  - Minimum Viable Architecture
  - Requirements Management
  - Service Delivery Model
```

---

## ------------------------------------------------------------------------------
## 3.6 Deliverables, Artifacts, and Building Blocks
## ------------------------------------------------------------------------------

```yaml
id: ARC-0005

name: Deliverables, Artifacts, and Building Blocks

category: Core Concept

source:
  chapter: 3
  section: 3.6

description:
  Architects executing the ADM produce architectural work products.
  The TOGAF Architecture Content Framework classifies these work
  products into Deliverables, Artifacts, and Building Blocks.

purpose:
  - Structure architecture work products
  - Standardize architecture outputs
  - Support architecture governance
  - Enable reusable architecture assets
  - Populate the Architecture Repository

core_elements:

  Deliverable:
    definition:
      - Contractually specified work product
      - Formally reviewed
      - Approved
      - Signed off by stakeholders

    characteristics:
      - Project output
      - May be archived
      - May become a reference model
      - May become a standard
      - May become an Architecture Landscape snapshot

  Artifact:
    definition:
      - Architectural work product describing an aspect of the architecture

    types:
      - Catalog
      - Matrix
      - Diagram

    examples:
      - Requirements Catalog
      - Application Interaction Matrix
      - Value Chain Diagram

    characteristics:
      - Forms the content of deliverables
      - Stored in the Architecture Repository
      - May or may not be a deliverable

  Building Block:
    definition:
      - Potentially reusable component combined with other building blocks to deliver architectures and solutions

    characteristics:
      - Reusable
      - Evolves in detail throughout ADM
      - Can be architecture-related
      - Can be solution-related

    levels:
      - Name
      - Outline Description
      - Full Specification
      - Decomposed Supporting Building Blocks

    types:

      Architecture Building Block (ABB):
        purpose:
          - Describe required capability
          - Specify Solution Building Blocks

        examples:
          - Customer Services Capability

      Solution Building Block (SBB):
        purpose:
          - Implement required capability
          - Realize architecture solutions

        examples:
          - Network
          - Processes
          - Data
          - Application Software

relationships:

  Deliverable:
    contains:
      - Artifact

  Artifact:
    describes:
      - Building Block

  Building Block:
    implemented_by:
      - Solution Building Block

  Architecture Building Block:
    specifies:
      - Solution Building Block

  Deliverables:
    archived_in:
      - Architecture Repository

  Artifacts:
    stored_in:
      - Architecture Repository

rules:
  - Every deliverable may contain one or more artifacts.
  - Every artifact describes one or more aspects of the architecture.
  - Artifacts may or may not be deliverables.
  - Building Blocks are reusable.
  - Architecture Building Blocks specify Solution Building Blocks.
  - Solution Building Blocks implement Architecture Building Blocks.
  - Building Blocks increase in detail as architecture development progresses.

validation:
  - Deliverables identified.
  - Artifacts identified.
  - Building Blocks identified.
  - ABBs mapped to SBBs.
  - Repository storage defined.
  - Deliverable-to-artifact relationships established.

related:
  - Architecture Development Method
  - Architecture Content Framework
  - Architecture Repository
  - Deliverable
  - Artifact
  - Building Block
  - Architecture Building Block
  - Solution Building Block
  - Architecture Definition Document
```

---

## ------------------------------------------------------------------------------
## 3.7 Architecture Abstraction
## ------------------------------------------------------------------------------

```yaml
id: ARC-0006

name: Architecture Abstraction

category: Core Concept

source:
  chapter: 3
  section: 3.7

definition:
  An architectural technique for dividing a problem area into smaller,
  easier-to-model and easier-to-solve problem areas.

purpose:
  - Reduce complexity
  - Improve understanding
  - Support architecture modeling
  - Separate concerns
  - Progress from high-level concepts to implementation

characteristics:
  - Layered
  - Hierarchical
  - Progressive
  - Cross-domain
  - Implementation-aware

fundamental_questions:

  Why:
    purpose:
      - Understand business motivation
      - Justify the architecture

  What:
    purpose:
      - Define required functionality
      - Define requirements

  How:
    purpose:
      - Define architecture structure
      - Organize functionality

  With What:
    purpose:
      - Determine implementation assets
      - Select physical technologies and components

abstraction_levels:

  Contextual:
    objective:
      - Understand enterprise environment
      - Define business context
      - Identify goals
      - Identify drivers
      - Identify objectives
      - Define scope

    answers:
      - Why is the architecture needed?

  Conceptual:
    objective:
      - Understand business requirements
      - Define required services
      - Focus on behavior
      - Avoid implementation details

    answers:
      - What is needed?

    models:
      - Business Services
      - Application Services
      - Technology Services

    aliases:
      - Service Abstraction
      - Behavior Abstraction

  Logical:
    objective:
      - Organize architecture components
      - Identify implementation-independent structure
      - Produce logical solution alternatives

    answers:
      - How should the architecture be structured?

    domains:
      - Business
      - Data
      - Application
      - Technology

  Physical:
    objective:
      - Allocate physical components
      - Implement logical architecture
      - Produce physical solution alternatives

    answers:
      - With what will the architecture be implemented?

relationships:

  Architecture Abstraction:
    consists_of:
      - Contextual
      - Conceptual
      - Logical
      - Physical

  Contextual:
    precedes:
      - Conceptual

  Conceptual:
    precedes:
      - Logical

  Logical:
    precedes:
      - Physical

  Physical:
    realizes:
      - Logical Architecture

rules:
  - Abstraction progresses from high-level to detailed models.
  - Every abstraction level answers a different architectural question.
  - Logical architecture remains implementation-independent.
  - Physical architecture realizes logical architecture.
  - Abstraction spans Business, Data, Application, and Technology domains.

validation:
  - Context defined.
  - Requirements identified.
  - Logical structure defined.
  - Physical implementation identified.
  - All abstraction levels connected.

related:
  - Architecture
  - Business Architecture
  - Data Architecture
  - Application Architecture
  - Technology Architecture
  - Logical Architecture
  - Physical Architecture
  - Services
```

---

## ------------------------------------------------------------------------------
## 3.8 Architecture Principles
## ------------------------------------------------------------------------------

```yaml
id: ARC-0007

name: Architecture Principles

category: Core Concept

source:
  chapter: 3
  section: 3.8

definition:
  Principles are general rules and guidelines, intended to be enduring
  and seldom amended, that inform and support the way in which an
  organization fulfills its mission.

purpose:
  - Guide architecture development
  - Support enterprise decision-making
  - Govern Enterprise Architecture
  - Align architecture with business objectives
  - Establish consistent architectural direction

characteristics:
  - Enduring
  - Stable
  - Consensus-driven
  - Decision-guiding
  - Governance-oriented

principle_domains:

  Enterprise Principles:
    purpose:
      - Guide enterprise-wide decision-making
      - Support fulfillment of organizational mission
      - Harmonize decisions across the enterprise
      - Support Architecture Governance

    examples:
      - Enterprise-wide principles
      - IT principles
      - HR principles
      - Domestic operations principles
      - Overseas operations principles

  Architecture Principles:
    purpose:
      - Guide architecture work
      - Govern architecture development
      - Govern architecture maintenance
      - Govern architecture use

    characteristics:
      - Reflect Enterprise Principles
      - Embody enterprise consensus
      - Form the basis for architecture decisions

hierarchy:

  Enterprise Principles:
    informs:
      - Segment Principles
      - Business Unit Principles
      - Architecture Principles

  Segment Principles:
    must_align_with:
      - Enterprise Principles

  Architecture Principles:
    derived_from:
      - Enterprise Principles

relationships:

  Architecture Principles:
    support:
      - Enterprise Architecture

  Architecture Principles:
    govern:
      - Architecture Development
      - Architecture Maintenance
      - Architecture Use

  Architecture Principles:
    align_with:
      - Business Objectives
      - Architecture Drivers

rules:
  - Principles should be enduring.
  - Principles should seldom be amended.
  - Architecture Principles shall reflect Enterprise Principles.
  - Architecture Principles shall support Architecture Governance.
  - Segment principles shall remain within the boundaries of Enterprise Principles.
  - Architecture Principles shall align with business objectives.
  - Architecture Principles shall align with key architecture drivers.
  - Architecture Principles provide the basis for future architecture decisions.

validation:
  - Enterprise Principles defined.
  - Architecture Principles defined.
  - Principles aligned with Enterprise Principles.
  - Principles aligned with business objectives.
  - Architecture drivers identified.
  - Governance supported.

related:
  - Enterprise Principles
  - Enterprise Architecture
  - Architecture Governance
  - Business Objectives
  - Architecture Drivers
  - Architecture Capability
```

---

## ------------------------------------------------------------------------------
## 3.9 Interoperability
## ------------------------------------------------------------------------------

```yaml
id: ARC-0008

name: Interoperability

category: Core Concept

source:
  chapter: 3
  section: 3.9

definition:
  The ability to share information and services.
  The degree to which information and services are shared is an
  important architectural requirement, particularly within complex
  organizations and extended enterprises.

purpose:
  - Enable information sharing
  - Enable service sharing
  - Support enterprise integration
  - Support collaboration
  - Establish interoperability requirements

characteristics:
  - Enterprise-wide
  - Cross-domain
  - Architecture requirement
  - Continuous throughout the ADM
  - Consistently defined

lifecycle:

  Phase A:
    name: Architecture Vision

    objective:
      - Identify information exchanges
      - Identify service exchanges
      - Capture security considerations
      - Establish business scenarios

  Phase B:
    name: Business Architecture

    objective:
      - Define information exchanges in business terms
      - Define service exchanges in business terms

  Phase C:
    Data Architecture:
      objective:
        - Define information exchange content
        - Develop corporate data model
        - Develop information exchange model

    Application Architecture:
      objective:
        - Define application information sharing
        - Define application service sharing

  Phase D:
    name: Technology Architecture

    objective:
      - Specify technical interoperability mechanisms
      - Enable information exchange
      - Enable service exchange

  Phase E:
    name: Opportunities and Solutions

    objective:
      - Select implementation solutions
      - Select Commercial Off-The-Shelf (COTS) solutions

  Phase F:
    name: Migration Planning

    objective:
      - Implement interoperability

relationships:

  Interoperability:
    spans:
      - Architecture Vision
      - Business Architecture
      - Data Architecture
      - Application Architecture
      - Technology Architecture
      - Opportunities and Solutions
      - Migration Planning

  Interoperability:
    enables:
      - Information Sharing
      - Service Sharing

rules:
  - Interoperability is an architectural requirement.
  - Interoperability shall be considered throughout the ADM.
  - Information exchanges shall be identified during Architecture Vision.
  - Business Architecture defines business information and service exchanges.
  - Data Architecture defines information exchange content.
  - Application Architecture defines application information and service sharing.
  - Technology Architecture specifies interoperability mechanisms.
  - Opportunities and Solutions selects implementation solutions.
  - Migration Planning implements interoperability.
  - A consistent definition of interoperability should be used across the enterprise.

validation:
  - Information exchanges identified.
  - Service exchanges identified.
  - Data exchange models defined.
  - Application integrations defined.
  - Technical interoperability mechanisms defined.
  - Implementation solution selected.
  - Interoperability implemented.

related:
  - Architecture Development Method
  - Architecture Vision
  - Business Architecture
  - Data Architecture
  - Application Architecture
  - Technology Architecture
  - Information Exchange
  - Service Exchange
  - Commercial Off-The-Shelf (COTS)
```


---

## ------------------------------------------------------------------------------
## 3.10 Enterprise Continuum
## ------------------------------------------------------------------------------

```yaml
id: ARC-0009

name: Enterprise Continuum

category: Core Concept

source:
  chapter: 3
  section: 3.10

definition:
  The Enterprise Continuum provides the broader context for
  Enterprise Architecture by enabling generic solutions to be
  leveraged and specialized to meet the needs of an individual
  organization.

purpose:
  - Classify architecture assets
  - Classify solution assets
  - Promote reuse
  - Support architecture evolution
  - Guide creation of organization-specific architectures

characteristics:
  - Categorization mechanism
  - Enterprise-wide
  - Reuse-oriented
  - Evolutionary
  - Repository-based

contains:

  Architecture Continuum:
    purpose:
      - Classify architecture assets
      - Classify architecture artifacts
      - Progress from generic to organization-specific architectures

  Solutions Continuum:
    purpose:
      - Classify solution assets
      - Classify solution artifacts
      - Progress from generic to organization-specific solutions

evolution:

  starts_with:
    - Foundation Architectures

  progresses_through:
    - Generic Architectures
    - Industry Architectures

  ends_with:
    - Organization-Specific Architectures

relationships:

  Enterprise Continuum:
    comprises:
      - Architecture Continuum
      - Solutions Continuum

  Enterprise Continuum:
    classifies:
      - Architecture Assets
      - Solution Assets
      - Architecture Artifacts
      - Solution Artifacts

  Enterprise Continuum:
    supported_by:
      - Architecture Repository

  Enterprise Continuum:
    supports:
      - Architecture Development Method

  Enterprise Continuum:
    enables:
      - Asset Reuse
      - Asset Specialization

rules:
  - Assets shall be classified within the Enterprise Continuum.
  - Assets evolve from generic to organization-specific applicability.
  - Generic assets should be reused where appropriate.
  - Organization-specific architectures are derived by specializing reusable assets.
  - The Enterprise Continuum consists of both the Architecture Continuum and the Solutions Continuum.

validation:
  - Architecture assets classified.
  - Solution assets classified.
  - Architecture Continuum defined.
  - Solutions Continuum defined.
  - Asset reuse identified.
  - Organization-specific architecture established.

related:
  - Architecture Continuum
  - Solutions Continuum
  - Architecture Repository
  - Foundation Architecture
  - Organization-Specific Architecture
  - Architecture Assets
  - Solution Assets
  - Architecture Development Method
```


---

## ------------------------------------------------------------------------------
## 3.11 Architecture Repository
## ------------------------------------------------------------------------------

```yaml
id: ARC-0010

name: Architecture Repository

category: Core Concept

source:
  chapter: 3
  section: 3.11

definition:
  The Architecture Repository stores architectural outputs created by
  the ADM at different levels of abstraction. It supports reuse,
  governance, and collaboration throughout the architecture lifecycle.

purpose:
  - Store architecture assets
  - Support architecture governance
  - Enable asset reuse
  - Support enterprise collaboration
  - Manage architecture knowledge

characteristics:
  - Central repository
  - Multi-level abstraction
  - Governance-enabled
  - Reuse-oriented
  - Supports the Enterprise Continuum

components:

  Architecture Metamodel:
    purpose:
      - Describe the organizational application of the architecture framework
      - Define the architecture content metamodel

  Architecture Capability:
    purpose:
      - Define governance structures
      - Define repository processes
      - Support repository management

  Architecture Landscape:
    purpose:
      - Represent enterprise architecture assets
      - Capture deployed and planned architectures
      - Maintain multiple abstraction levels

  Standards Library:
    purpose:
      - Store standards
      - Define compliance requirements
      - Guide new architectures

  Reference Library:
    purpose:
      - Store reusable guidelines
      - Store templates
      - Store patterns
      - Store reference material

  Governance Repository:
    purpose:
      - Store governance processes
      - Store governance records
      - Support architecture governance

  Architecture Requirements Repository:
    purpose:
      - Store architecture requirements
      - Support requirements management
      - Maintain requirement traceability

relationships:

  Architecture Repository:
    supports:
      - Architecture Development Method
      - Enterprise Continuum

  Architecture Repository:
    contains:
      - Architecture Metamodel
      - Architecture Capability
      - Architecture Landscape
      - Standards Library
      - Reference Library
      - Governance Repository
      - Architecture Requirements Repository

  Architecture Repository:
    stores:
      - Architecture Outputs
      - Architecture Assets
      - Architecture Artifacts

rules:
  - Architecture outputs shall be stored in the Architecture Repository.
  - Assets may exist at multiple levels of abstraction.
  - New architectures shall comply with the Standards Library.
  - The Repository shall support governance activities.
  - The Repository shall support reuse through the Enterprise Continuum.
  - Requirements shall be maintained within the Architecture Requirements Repository.

validation:
  - Repository established.
  - Repository components defined.
  - Architecture assets stored.
  - Standards available.
  - Governance supported.
  - Requirements repository maintained.
  - Multiple abstraction levels supported.

related:
  - Enterprise Continuum
  - Architecture Development Method
  - Architecture Metamodel
  - Architecture Capability
  - Architecture Landscape
  - Standards Library
  - Reference Library
  - Governance Repository
  - Architecture Requirements Repository
```

---

## ------------------------------------------------------------------------------
## 3.12.1 TOGAF Content Framework and Enterprise Metamodel — Overview
## ------------------------------------------------------------------------------

```yaml
id: ARC-0011

name: TOGAF Content Framework and Enterprise Metamodel Overview

category: Core Concept

source:
  chapter: 3
  section: 3.12.1

definition:
  The TOGAF ADM provides lifecycle management for creating and
  managing Enterprise Architectures. During the Preliminary Phase,
  an enterprise establishes a Content Framework and an Enterprise
  Metamodel to organize, describe, store, and analyze architecture
  content.

purpose:
  - Structure Architecture Descriptions
  - Organize architecture work products
  - Define enterprise entities
  - Define relationships between enterprise entities
  - Support Enterprise Architecture Capability

characteristics:
  - ADM-based
  - Enterprise-specific
  - Repository-oriented
  - Framework-driven
  - Metamodel-driven

core_elements:

  Content Framework:
    purpose:
      - Categorize Architecture Descriptions
      - Structure architecture work products
      - Organize architecture models

  Enterprise Metamodel:
    purpose:
      - Define enterprise entities
      - Define relationships between entities
      - Support storing architecture information
      - Support analysis of architecture information

  Architecture Artifacts:
    purpose:
      - Represent architecture content
      - Express Architecture Descriptions

selection_factors:

  influenced_by:
    - Selected Architecture Framework
    - Software tool supporting the Enterprise Architecture Capability

relationships:

  Preliminary Phase:
    establishes:
      - Content Framework
      - Enterprise Metamodel

  Content Framework:
    structures:
      - Architecture Descriptions
      - Architecture Artifacts
      - Architecture Models

  Enterprise Metamodel:
    defines:
      - Enterprise Entities
      - Entity Relationships

  Enterprise Metamodel:
    supports:
      - Architecture Description

rules:
  - The Content Framework shall categorize Architecture Descriptions.
  - The Enterprise Metamodel shall define enterprise entities and their relationships.
  - Both shall be established during the Preliminary Phase.
  - The selected Content Framework may be adapted to enterprise needs.
  - The choice of framework may be influenced by the selected architecture framework and supporting software tools.

validation:
  - Content Framework defined.
  - Enterprise Metamodel defined.
  - Architecture artifacts identified.
  - Enterprise entities identified.
  - Entity relationships defined.
  - Preliminary Phase outputs completed.

related:
  - Architecture Development Method
  - Preliminary Phase
  - Content Framework
  - Enterprise Metamodel
  - Architecture Description
  - Architecture Artifact
  - Enterprise Architecture Capability
```

---

## ------------------------------------------------------------------------------
## 3.12.2 Content Framework
## ------------------------------------------------------------------------------

```yaml
id: ARC-0012

name: TOGAF Content Framework

category: Core Concept

source:
  chapter: 3
  section: 3.12.2

definition:
  The Content Framework defines a categorization framework used to
  describe the building blocks and artifacts that reflect decisions made
  in creating the overall architecture deliverables.

purpose:
  - Structure architectural work products
  - Categorize building blocks
  - Categorize architecture artifacts
  - Support Architecture Repository organization
  - Ensure consistent architecture outputs

characteristics:
  - Categorization framework
  - Enterprise-specific
  - Repository-oriented
  - ADM-aligned
  - Adaptable

repository_support:

  Architecture Repository:
    stores:
      - Artifacts
      - Work Products
      - Content Framework outputs

framework_objectives:
  - Provide a detailed model of architectural work products
  - Drive consistency in ADM outputs
  - Provide a comprehensive checklist of architecture outputs
  - Reduce the risk of gaps in architecture deliverables
  - Help mandate standard architecture concepts, terms, and deliverables

alternative_frameworks:
  - TOGAF Content Framework
  - Zachman Framework
  - DoDAF
  - NAF

structure:

  aligned_with:
    - Preliminary Phase
    - Architecture Vision
    - Business Architecture
    - Information Systems Architectures
    - Technology Architecture
    - Architecture Realization / Transformation
    - Architecture Change Management

  model_groups:

    Architecture Principles, Vision, Motivation, and Requirements:
      captures:
        - Architecture Principles
        - Strategic context
        - Requirements
        - Architecture motivation

    Business Architecture:
      captures:
        - Business motivation
        - Business structure
        - Business capabilities

    Information Systems Architectures:
      captures:
        - Applications
        - Data

    Technology Architecture:
      captures:
        - Technology assets
        - Technology implementation

    Architecture Realization / Transformation:
      captures:
        - Change roadmaps
        - Transition between architecture states
        - Binding statements for implementation governance

    Architecture Change Management:
      captures:
        - Value realization management events
        - Internal events
        - External events
        - Requirements for action

relationships:

  Content Framework:
    structures:
      - Building Blocks
      - Artifacts
      - Architecture Deliverables

  Content Framework:
    supports:
      - Architecture Repository
      - Architecture Development Method

  Content Framework:
    aligned_with:
      - ADM Phases

rules:
  - The Content Framework shall categorize architectural work products.
  - The Architecture Repository shall store artifacts and work products identified by the Content Framework.
  - The Content Framework shall be aligned with the ADM.
  - The selected framework may be adapted to enterprise-specific needs.
  - Selection of a Content Framework is essential regardless of which framework is chosen.

validation:
  - Content Framework selected.
  - Architecture work products categorized.
  - Repository structure defined.
  - ADM alignment established.
  - Architecture outputs complete.
  - Deliverable gaps minimized.

related:
  - Architecture Repository
  - Architecture Development Method
  - Enterprise Metamodel
  - Building Blocks
  - Artifacts
  - Architecture Deliverables
  - Preliminary Phase
```

---

## ------------------------------------------------------------------------------
## 3.12.3 Enterprise Metamodel
## ------------------------------------------------------------------------------

```yaml
id: ARC-0013

name: Enterprise Metamodel

category: Core Concept

source:
  chapter: 3
  section: 3.12.3

definition:
  The Enterprise Metamodel defines the types of entity that appear
  in the models describing the enterprise, together with the
  relationships between those entities.

purpose:
  - Define enterprise entity types
  - Define relationships between entities
  - Support Architecture Descriptions
  - Support architecture modeling
  - Support enterprise analysis

characteristics:
  - Enterprise-specific
  - Formal model
  - Relationship-based
  - Extensible
  - Supports architecture modeling

entities:

  examples:
    - Role

  role_examples:
    - Teller
    - Pilot
    - Manager
    - Volunteer
    - Customer
    - Firefighter

value:
  - Provides architects with a starter set of entity types to investigate and model.
  - Provides a completeness check for an architecture modeling language or architecture metamodel.
  - Helps ensure consistency.
  - Helps ensure completeness.
  - Helps ensure traceability.

does_not_constrain:
  - Selection of artifacts
  - Modeling notation

supported_modeling_languages:
  - ArchiMate®
  - Business Process Modeling Notation™ (BPMN™)
  - Unified Modeling Language™ (UML®)
  - Entity relationship diagramming
  - Flowcharting
  - Any notation capable of expressing TOGAF concepts

relationships:

  Enterprise Metamodel:
    defines:
      - Entity Types
      - Entity Relationships

  Enterprise Metamodel:
    supports:
      - Architecture Description
      - Architecture Modeling

  Enterprise Metamodel:
    improves:
      - Consistency
      - Completeness
      - Traceability

  Enterprise Metamodel:
    developed_as_part_of:
      - Enterprise Architecture Capability

rules:
  - The Enterprise Metamodel shall define entity types.
  - The Enterprise Metamodel shall define relationships between entity types.
  - Entity types and relationships are specific to the individual enterprise.
  - The Enterprise Metamodel shall support Architecture Descriptions.
  - The TOGAF Standard does not constrain artifact selection.
  - The TOGAF Standard does not constrain modeling notation.

validation:
  - Entity types defined.
  - Entity relationships defined.
  - Architecture Description supported.
  - Consistency achieved.
  - Completeness verified.
  - Traceability established.
  - Enterprise-specific metamodel defined.

related:
  - Content Framework
  - Architecture Description
  - Enterprise Architecture Capability
  - Architecture Modeling
  - ArchiMate®
  - BPMN™
  - UML®
```

---

## ------------------------------------------------------------------------------
## 3.12.4 Developing the Enterprise Metamodel
## ------------------------------------------------------------------------------

```yaml
id: ARC-0014

name: Developing the Enterprise Metamodel

category: Core Concept

source:
  chapter: 3
  section: 3.12.4

definition:
  The Enterprise Metamodel is an important part of the
  Organization-Specific Architecture Framework. Its development is
  supported by the Enterprise Continuum and the Foundation-level
  Core Enterprise Metamodel provided in the TOGAF Library.

purpose:
  - Develop an enterprise-specific metamodel
  - Support enterprise architecture modeling
  - Reuse foundation-level metamodel resources
  - Provide context for ADM artifacts

characteristics:
  - Organization-specific
  - Enterprise Continuum supported
  - Foundation-based
  - Reusable
  - Extensible

development_support:

  Enterprise Continuum:
    provides:
      - A progression from Foundation resources
      - A progression to Organization-Specific resources

  TOGAF Library:
    provides:
      - Foundation-level Core Enterprise Metamodel

Foundation Core Enterprise Metamodel:

  contains:
    - Types of entity
    - Relationships between entities

  purpose:
    - Support modeling of most enterprises
    - Provide context for ADM artifacts

relationships:

  Enterprise Metamodel:
    part_of:
      - Organization-Specific Architecture Framework

  Enterprise Metamodel:
    supported_by:
      - Enterprise Continuum
      - TOGAF Library

  Enterprise Continuum:
    progresses_from:
      - Foundation

  Enterprise Continuum:
    progresses_to:
      - Organization-Specific

  Foundation Core Enterprise Metamodel:
    provides:
      - Entity types
      - Entity relationships
      - Context for ADM artifacts

rules:
  - The Enterprise Metamodel is an important part of the Organization-Specific Architecture Framework.
  - Development of the Enterprise Metamodel is supported by the Enterprise Continuum.
  - The TOGAF Library provides a Foundation-level Core Enterprise Metamodel.
  - The Foundation Core Enterprise Metamodel provides entity types and relationships likely to be required by most enterprises.
  - The Foundation Core Enterprise Metamodel provides context for the artifacts suggested in the ADM.

validation:
  - Organization-specific metamodel established.
  - Foundation Core Enterprise Metamodel referenced.
  - Enterprise Continuum applied.
  - Entity types identified.
  - Entity relationships identified.
  - ADM artifact context established.

related:
  - Enterprise Metamodel
  - Enterprise Continuum
  - TOGAF Library
  - Organization-Specific Architecture Framework
  - Foundation Core Enterprise Metamodel
  - Architecture Development Method
```

---

## ------------------------------------------------------------------------------
## 3.13 Establishing and Maintaining an Enterprise Architecture Capability
## ------------------------------------------------------------------------------

```yaml
id: ARC-0015

name: Establishing and Maintaining an Enterprise Architecture Capability

category: Core Concept

source:
  chapter: 3
  section: 3.13

definition:
  To carry out architectural activity effectively within an enterprise,
  it is necessary to establish an appropriate business capability for
  architecture through organization structures, roles,
  responsibilities, skills, and processes.

purpose:
  - Enable effective architectural activity
  - Establish an Enterprise Architecture Capability
  - Provide the organizational foundation for architecture work

characteristics:
  - Business capability
  - Organization-wide
  - Role-based
  - Process-driven
  - Skills-oriented

capability_components:
  - Organization Structures
  - Roles
  - Responsibilities
  - Skills
  - Processes

relationships:

  Enterprise Architecture Capability:
    enables:
      - Architectural Activity

  Enterprise Architecture Capability:
    established_through:
      - Organization Structures
      - Roles
      - Responsibilities
      - Skills
      - Processes

rules:
  - An appropriate business capability for architecture shall be established.
  - Architecture capability shall include organization structures.
  - Architecture capability shall define roles.
  - Architecture capability shall define responsibilities.
  - Architecture capability shall include the necessary skills.
  - Architecture capability shall be supported by defined processes.

validation:
  - Organization structures established.
  - Roles defined.
  - Responsibilities assigned.
  - Required skills identified.
  - Processes established.
  - Enterprise Architecture Capability operational.

related:
  - Enterprise Architecture Capability
  - Architecture Development Method
  - Organization Structures
  - Roles
  - Responsibilities
  - Skills
  - Processes
```

---

## ------------------------------------------------------------------------------
## 3.14 Establishing the Architecture Capability as an Operational Entity
## ------------------------------------------------------------------------------

```yaml
id: ARC-0016

name: Establishing the Architecture Capability as an Operational Entity

category: Core Concept

source:
  chapter: 3
  section: 3.14

definition:
  A successful Enterprise Architecture practice should operate as a
  business function with a firm operational footing. In addition to the
  core ADM processes, the practice should establish operational
  management capabilities.

purpose:
  - Operate the Enterprise Architecture practice effectively
  - Support ongoing architecture operations
  - Manage the Architecture Capability as a business function
  - Complement the ADM with operational capabilities

characteristics:
  - Operational
  - Business-oriented
  - Governance-supported
  - Service-oriented
  - Management-focused

operational_capabilities:
  - Financial Management
  - Performance Management
  - Service Management
  - Risk and Opportunity Management
  - Resource Management
  - Communications and Stakeholder Management
  - Quality Management
  - Supplier Management
  - Configuration Management
  - Environment Management

governance:

  Architecture Governance:
    purpose:
      - Control architecturally significant activities
      - Align activities within a single governance framework

benefits:
  - Increased transparency of accountability
  - Informed delegation of authority
  - Proactive risk and opportunity management
  - Protection of existing assets through reuse
  - Proactive control, monitoring, and management
  - Process, concept, and component reuse
  - Value creation through monitoring, measurement, evaluation, and feedback
  - Increased visibility for internal and external stakeholders
  - Greater shareholder value
  - Integration with existing processes and methodologies

relationships:

  Enterprise Architecture Practice:
    operates_as:
      - Operational Entity
      - Business Function

  Enterprise Architecture Practice:
    supported_by:
      - Architecture Governance
      - Operational Management Capabilities

  Architecture Governance:
    controls:
      - Architecturally Significant Activities

rules:
  - The Enterprise Architecture practice should operate as a business.
  - Operational management capabilities should complement the ADM.
  - Architecturally significant activities should be governed within a single framework.
  - Governance should provide visibility, guidance, and control.
  - Governance should integrate with existing enterprise processes and methodologies.

validation:
  - Operational capability established.
  - Financial management implemented.
  - Performance management implemented.
  - Service management implemented.
  - Governance framework operational.
  - Operational management capabilities established.

related:
  - Enterprise Architecture Capability
  - Architecture Governance
  - Architecture Development Method
  - Financial Management
  - Performance Management
  - Service Management
  - Communications and Stakeholder Management
  - Quality Management
  - Configuration Management
```

---

## ------------------------------------------------------------------------------
## 3.15 Using the TOGAF Standard with Other Frameworks
## ------------------------------------------------------------------------------

```yaml
id: ARC-0017

name: Using the TOGAF Standard with Other Frameworks

category: Core Concept

source:
  chapter: 3
  section: 3.15

definition:
  The TOGAF Standard is a generic Enterprise Architecture framework
  that provides a flexible and extensible content framework. It may
  be used independently or tailored and integrated with other
  architecture frameworks, methodologies, and best practices.

purpose:
  - Support framework integration
  - Enable architecture tailoring
  - Extend architecture deliverables
  - Support enterprise-specific methods

characteristics:
  - Generic
  - Flexible
  - Extensible
  - Tailorable
  - Framework-independent

key_elements:
  - Definition of architecture deliverables
  - Description of the architecture development method

framework_position:
  majority_of_frameworks:
    focus_on:
      - Architecture deliverables

    generally_do_not_focus_on:
      - Methods for producing deliverables

  TOGAF:
    provides:
      - Generic architecture deliverables
      - Flexible content framework
      - Architecture development method

usage_options:
  - Use the TOGAF Standard independently.
  - Replace TOGAF deliverables with framework-specific deliverables.
  - Extend TOGAF deliverables.
  - Tailor the TOGAF framework for enterprise needs.
  - Integrate TOGAF with other frameworks and best practices.
  - Adopt reference material from the TOGAF Library.

example_integrations:
  - ITIL®
  - CMMI®
  - COBIT®
  - PRINCE2
  - PMBOK
  - MSP®

example_reference_material:
  - IT4IT™ Reference Architecture

relationships:

  TOGAF Standard:
    provides:
      - Architecture Deliverables
      - Architecture Development Method

  TOGAF Standard:
    integrates_with:
      - Other Enterprise Architecture Frameworks
      - Best Practices
      - Enterprise Processes

  TOGAF Library:
    provides:
      - Reference Materials

rules:
  - The TOGAF framework may be used independently.
  - TOGAF deliverables may be replaced or extended.
  - The architecture method should be tailored to the enterprise.
  - TOGAF methods may be integrated with other frameworks and best practices.
  - Reference material from the TOGAF Library may be adopted where appropriate.

validation:
  - Architecture method tailored.
  - Enterprise integration completed.
  - Deliverables defined.
  - Framework integration established.
  - Reference material identified.

related:
  - Architecture Development Method
  - TOGAF Library
  - Architecture Deliverables
  - ITIL®
  - CMMI®
  - COBIT®
  - PRINCE2
  - PMBOK
  - MSP®
```

---

## ------------------------------------------------------------------------------
## 3.16 Using the TOGAF Framework with Different Architecture Styles
## ------------------------------------------------------------------------------

```yaml
id: ARC-0018

name: Using the TOGAF Framework with Different Architecture Styles

category: Core Concept

source:
  chapter: 3
  section: 3.16

definition:
  The TOGAF framework is designed to be flexible and can be readily
  adapted to support a variety of architectural styles while ensuring
  that stakeholder concerns are addressed.

purpose:
  - Support multiple architectural styles
  - Adapt the TOGAF framework to different contexts
  - Address stakeholder concerns
  - Select appropriate architecture resources

characteristics:
  - Generic
  - Flexible
  - Extensible
  - Adaptable
  - Style-independent

architecture_styles:
  differ_by:
    - Focus
    - Form
    - Techniques
    - Materials
    - Subject
    - Time period

principles:
  - The Architecture Landscape can contain multiple architectural styles.
  - Stakeholder needs shall be addressed in the context of other stakeholders and the Baseline Architecture.
  - The framework should be adapted by changing models, viewpoints, and tools rather than changing the framework itself.

practitioner_process:

  step_1:
    Identify the distinctive features of the architectural style.

  step_2:
    Determine how the distinctive features will be addressed.

  step_3:
    Select the appropriate:
      - Models
      - Viewpoints
      - Tools

  step_4:
    Demonstrate that stakeholder concerns are addressed.

architecture_impacts:
  distinctive_features_may:
    - Add new architectural elements
    - Highlight existing elements
    - Adjust notation
    - Focus on specific stakeholders
    - Focus on stakeholder concerns

may_require:
  - Extensions to the Architecture Content Metamodel
  - Specific notation
  - Modeling techniques
  - Identification of viewpoints

adm_considerations:
  phases:
    - Phase B
    - Phase C
    - Phase D

  possible_action:
    - Revisit the Preliminary Phase
    - Modify the Architecture Capability
    - Address style-specific scope

supporting_resources:
  - Style-specific reference models
  - Style-specific maturity models

example_guides:
  - TOGAF® Series Guide: Using the TOGAF® Framework to Define and Govern Service-Oriented Architectures
  - TOGAF® Series Guide: Integrating Risk and Security within a TOGAF® Enterprise Architecture
  - TOGAF® and SABSA® Integration
  - Archi Banking Group: Combining the BIAN Reference Model, ArchiMate® Modeling Notation, and the TOGAF® Framework
  - Exploring Synergies between TOGAF® and Frameworx
  - TOGAF® 9 and DoDAF 2.0

relationships:

  TOGAF Framework:
    supports:
      - Multiple Architecture Styles

  Practitioner:
    selects:
      - Models
      - Viewpoints
      - Tools

  Distinctive Features:
    may_require:
      - Architecture Content Metamodel Extensions
      - Specific Modeling Techniques
      - Viewpoints

rules:
  - Architectural styles shall first be identified.
  - Distinctive features shall be analyzed before adaptation.
  - The TOGAF framework itself should not require significant changes.
  - Models, viewpoints, and tools should be adjusted to support the selected style.
  - Stakeholder concerns shall be demonstrated in Phases B, C, and D.

validation:
  - Architectural style identified.
  - Distinctive features documented.
  - Appropriate models selected.
  - Appropriate viewpoints selected.
  - Appropriate tools selected.
  - Stakeholder concerns addressed.
  - Required metamodel extensions identified.

related:
  - Architecture Development Method
  - Architecture Content Metamodel
  - Architecture Capability
  - Architecture Landscape
  - Baseline Architecture
  - Architecture Views
  - Viewpoints
```

---

## ------------------------------------------------------------------------------
## 3.17 Architecture Views and Viewpoints
## ------------------------------------------------------------------------------

```yaml
id: ARC-0019

name: Architecture Views and Viewpoints

category: Core Concept

source:
  chapter: 3
  section: 3.17

definition:
  The ability to create specific views of parts of a complex
  architecture is fundamental to communicating with stakeholders
  and addressing their concerns. Information should be presented in
  a form that each stakeholder can understand and relate to.

purpose:
  - Communicate architecture effectively
  - Address stakeholder concerns
  - Improve stakeholder understanding
  - Gain stakeholder support

characteristics:
  - Stakeholder-focused
  - Concern-driven
  - Communication-oriented
  - Architecture-specific
  - Standards-based

principles:
  - Complex architectures should be presented through specific views.
  - Information should be tailored to individual stakeholders.
  - Views exist to communicate and address stakeholder concerns.
  - Stakeholder understanding is necessary to obtain stakeholder support.

core_concepts:
  - Stakeholder
  - Concern
  - Viewpoint
  - View
  - Model
  - System

relationships:

  Stakeholder:
    has:
      - Concerns

  Viewpoint:
    frames:
      - Concerns

  Viewpoint:
    governs:
      - View

  View:
    addresses:
      - Stakeholder Concerns

  View:
    consists_of:
      - Models

  Models:
    describe:
      - System

standards_basis:
  - ISO/IEC/IEEE 42010:2011
  - ISO/IEC/IEEE 15288:2015

rules:
  - Architecture information shall be presented using views.
  - Views shall address stakeholder concerns.
  - Information shall be presented in a form stakeholders understand.
  - Views shall be created according to viewpoints.

validation:
  - Stakeholders identified.
  - Stakeholder concerns identified.
  - Appropriate viewpoints selected.
  - Architecture views created.
  - Views communicate architecture effectively.
  - Stakeholder understanding achieved.

related:
  - Stakeholder
  - Concern
  - View
  - Viewpoint
  - Model
  - Architecture Description
  - ISO/IEC/IEEE 42010
  - ISO/IEC/IEEE 15288
```

---

## ------------------------------------------------------------------------------
## 3.18 Enterprise Agility
## ------------------------------------------------------------------------------

```yaml
id: ARC-0020

name: Enterprise Agility

category: Core Concept

source:
  chapter: 3
  section: 3.18

definition:
  Enterprise agility is a commonly used term whose exact definition
  differs among practitioners. Regardless of the definition used, it is
  important because it enables an enterprise to better react to
  change by being more customer- and product-centric, more
  efficient, and better able to ensure regulatory compliance.

purpose:
  - Enable rapid response to change
  - Improve customer centricity
  - Improve product centricity
  - Increase enterprise efficiency
  - Support regulatory compliance

characteristics:
  - Customer-centric
  - Product-centric
  - Change-oriented
  - Efficient
  - Adaptive

principles:
  - Enterprise agility extends beyond agile software development.
  - Enterprise Architecture provides a framework for change.
  - Enterprise Architecture links change to strategic direction and business value.
  - Enterprise Architecture manages complexity.
  - Enterprise Architecture supports continuous change.
  - Enterprise Architecture manages the risk of unanticipated consequences.

supporting_mechanisms:
  - Partitions
  - Levels
  - Iteration

mechanisms_description:

  partitions:
    purpose: Define how work is broken down into multiple architecture initiatives.

  levels:
    purpose: Define how the architecture is developed at different levels of granularity and detail.

  iteration:
    purpose: Support iterative development through the TOGAF ADM.

adaptation_guidance:
  - Apply agile principles and techniques where appropriate.
  - Employ additional techniques to support an agile enterprise.
  - Adapt the TOGAF ADM to support enterprise agility.

supporting_guides:
  - TOGAF® Series Guide: Applying the ADM Using Agile Sprints
  - TOGAF® Series Guide: Enabling Enterprise Agility
  - The Open Agile Architecture™ Standard

relationships:

  Enterprise Agility:
    enabled_by:
      - Enterprise Architecture

  Enterprise Architecture:
    provides:
      - Framework for Change

  Enterprise Architecture:
    supports:
      - Continuous Change
      - Complexity Management
      - Strategic Direction
      - Business Value

  TOGAF ADM:
    supports:
      - Iteration

  Partitions:
    define:
      - Multiple Architecture Initiatives

  Levels:
    define:
      - Granularity
      - Detail

rules:
  - Enterprise agility shall not be treated as synonymous with agile software development.
  - Enterprise Architecture should be used to support continuous organizational change.
  - Architecture work may be partitioned into multiple initiatives.
  - Architecture may be developed at different levels of granularity.
  - The ADM may be adapted to support enterprise agility.

validation:
  - Architecture initiatives partitioned where appropriate.
  - Architecture levels defined.
  - Iterative development applied.
  - Enterprise Architecture aligned with strategic direction.
  - Continuous change supported.
  - Risks of unanticipated consequences managed.

related:
  - Enterprise Architecture
  - Architecture Development Method
  - Partitions
  - Levels
  - Iteration
  - Open Agile Architecture™ Standard
```

---

## ------------------------------------------------------------------------------
## 3.19 Risk Management
## ------------------------------------------------------------------------------

```yaml
id: ARC-0021

name: Risk Management

category: Core Concept

source:
  chapter: 3
  section: 3.19

definition:
  There will always be risk associated with architecture and business
  transformation efforts. Risks should be identified, classified, and
  mitigated before transformation begins, and monitored throughout
  the transformation effort.

purpose:
  - Identify transformation risks
  - Classify risks
  - Mitigate risks
  - Monitor risks throughout transformation
  - Support governance-based risk management

characteristics:
  - Continuous
  - Governance-driven
  - Transformation-focused
  - Proactive
  - Iterative

principles:
  - Risk exists in every architecture and business transformation effort.
  - Risks should be identified before transformation begins.
  - Risk mitigation is an ongoing activity.
  - Risk triggers may originate outside the transformation effort.
  - Risks must first be accepted within the governance framework before they are managed.

risk_levels:

  initial_risk:
    description: Risk categorization prior to determining and implementing mitigating actions.

  residual_risk:
    description: Risk categorization after mitigating actions have been implemented.

risk_management_process:
  - Risk Classification
  - Risk Identification
  - Initial Risk Assessment
  - Risk Mitigation and Residual Risk Assessment
  - Risk Monitoring

governance:
  Enterprise_Architect:
    responsibilities:
      - Identify risks
      - Mitigate certain risks

  Governance_Framework:
    responsibilities:
      - Accept risks
      - Manage accepted risks

supporting_guidance:
  - TOGAF Standard — ADM Techniques (qualitative risk management)
  - TOGAF® Series Guide: Integrating Risk and Security within a TOGAF® Enterprise Architecture
  - Open FAIR™ Body of Knowledge
  - Open Risk Taxonomy (O-RT)
  - Open Risk Analysis (O-RA)

relationships:

  Risk_Management:
    consists_of:
      - Risk Classification
      - Risk Identification
      - Initial Risk Assessment
      - Risk Mitigation
      - Residual Risk Assessment
      - Risk Monitoring

  Enterprise_Architect:
    identifies:
      - Risks

  Governance_Framework:
    accepts_and_manages:
      - Risks

rules:
  - Risks shall be identified before transformation begins.
  - Risks shall be classified prior to mitigation.
  - Risk mitigation shall be continuous throughout the transformation.
  - External risk triggers shall be monitored.
  - Risks shall be accepted through the governance framework before management actions are applied.

validation:
  - Risks identified.
  - Risks classified.
  - Initial risk assessment completed.
  - Mitigation actions defined.
  - Residual risk assessed.
  - Risk monitoring established.
  - Governance acceptance documented.

related:
  - Architecture Governance
  - Enterprise Architecture
  - Architecture Development Method
  - ADM Techniques
  - Open FAIR™ Body of Knowledge
  - Open Risk Taxonomy (O-RT)
  - Open Risk Analysis (O-RA)
```
