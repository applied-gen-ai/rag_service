# ============================================================================
# Terraform Infrastructure Cleanup Script (ASCII SAFE VERSION)
# ============================================================================

param(
    [switch]$AutoApprove,
    [switch]$DryRun,
    [switch]$Force
)

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "============================================"
Write-Host "TERRAFORM INFRASTRUCTURE CLEANUP"
Write-Host "============================================"
Write-Host ""

# ============================================================================
# Helper Functions
# ============================================================================

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "[STEP] $Message"
}

function Write-Success {
    param([string]$Message)
    Write-Host "  [OK] $Message"
}

function Write-Info {
    param([string]$Message)
    Write-Host "  [INFO] $Message"
}

function Write-Warning {
    param([string]$Message)
    Write-Host "  [WARN] $Message"
}

function Write-ErrorMsg {
    param([string]$Message)
    Write-Host "  [ERROR] $Message"
}

# ============================================================================
# Pre-flight Checks
# ============================================================================

Write-Step "Step 1/5: Pre-flight Checks"

# Check if terraform is installed
Write-Info "Checking Terraform availability..."
try {
    $terraformVersion = terraform --version 2>$null | Select-Object -First 1
    if ($terraformVersion) {
        Write-Success "Terraform found: $terraformVersion"
    } else {
        Write-ErrorMsg "Terraform not found in PATH"
        exit 1
    }
} catch {
    Write-ErrorMsg "Error checking Terraform"
    exit 1
}

# Check for *.tf files
if (-not (Test-Path "*.tf")) {
    Write-ErrorMsg "No Terraform files found in this directory"
    exit 1
}

Write-Success "Terraform files detected"

# Check Terraform state
if (-not (Test-Path "terraform.tfstate") -and -not (Test-Path ".terraform")) {
    Write-Warning "No Terraform state detected. Nothing to destroy."
    exit 0
}

Write-Success "Terraform state found"

# ============================================================================
# Show resources
# ============================================================================

Write-Step "Step 2/5: Checking Resources"

Write-Info "Listing resources..."
try {
    $resourceList = terraform state list 2>$null
    $resourceCount = $resourceList.Count

    if ($resourceCount -eq 0) {
        Write-Warning "No resources found in state"
        exit 0
    }

    Write-Success "$resourceCount resources found"
    Write-Host ""
    Write-Host "Resources to be destroyed:"
    foreach ($r in $resourceList) {
        Write-Host "   - $r"
    }
} catch {
    Write-Warning "Could not read state"
}

# ============================================================================
# Output summary
# ============================================================================

Write-Step "Step 3/5: Output Summary"

try {
    $albDns = terraform output -raw alb_dns_name 2>$null
    $clusterName = terraform output -raw ecs_cluster_name 2>$null
    $serviceName = terraform output -raw ecs_service_name 2>$null

    if ($albDns) {
        Write-Host ""
        Write-Host "Deployment Summary:"
        Write-Host "   ALB DNS:        $albDns"
        Write-Host "   ECS Cluster:    $clusterName"
        Write-Host "   ECS Service:    $serviceName"
    }
} catch {}

# ============================================================================
# Confirmation
# ============================================================================

Write-Step "Step 4/5: Confirmation"

if ($DryRun) {
    Write-Host ""
    Write-Host "DRY RUN ENABLED - No resources will be deleted."
    terraform plan -destroy
    exit 0
}

if (-not $AutoApprove -and -not $Force) {
    Write-Host ""
    Write-Host "WARNING: THIS ACTION WILL DELETE EVERYTHING!"
    Write-Host "Type DESTROY to confirm:"
    $input = Read-Host

    if ($input -ne "DESTROY") {
        Write-Warning "User cancelled."
        exit 0
    }
}

# ============================================================================
# Destroy
# ============================================================================

Write-Step "Step 5/5: Destroying Infrastructure"

$startTime = Get-Date

try {
    terraform destroy -auto-approve
    if ($LASTEXITCODE -eq 0) {
        $endTime = Get-Date
        $duration = $endTime - $startTime

        Write-Host ""
        Write-Success "All resources destroyed successfully"
        Write-Info "Time taken: $($duration.Minutes)m $($duration.Seconds)s"

        Write-Host ""
        Write-Host "Cleaned Resources:"
        Write-Host "   - ECS Services"
        Write-Host "   - ECS Cluster"
        Write-Host "   - Load Balancer"
        Write-Host "   - Target Groups"
        Write-Host "   - IAM Roles"
        Write-Host "   - CloudWatch Logs"

    } else {
        Write-ErrorMsg "Terraform destroy failed"
        exit 1
    }
} catch {
    Write-ErrorMsg "Exception during destroy"
    exit 1
}

# ============================================================================
# Post-Destroy Check
# ============================================================================

Write-Host ""
Write-Host "VERIFICATION"
Write-Host "============"

try {
    $remaining = terraform state list 2>$null
    if ($remaining.Count -eq 0) {
        Write-Success "No resources remaining"
    } else {
        Write-Warning "Some resources still remain:"
        foreach ($r in $remaining) {
            Write-Host "   - $r"
        }
    }
} catch {}

Write-Host ""
Write-Host "NEXT STEPS:"
Write-Host "   terraform apply (to redeploy)"
Write-Host ""
