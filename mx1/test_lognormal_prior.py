import torch
from torch.distributions import Distribution, constraints, LogNormal, Independent
from sbi.utils import RestrictionEstimator
from sbi.utils.user_input_checks import process_prior

class TruncatedLogNormalPrior(Distribution):
    arg_constraints = {}
    support = constraints.real_vector

    def __init__(self, num_dim: int, low: torch.Tensor, high: torch.Tensor, device: torch.device):
        self.num_dim = num_dim
        self.device = device
        self.low = low
        self.high = high
        self.loc = torch.zeros(num_dim, device=device)
        self.scale = torch.ones(num_dim, device=device) * 0.4
        
        self.base_dist = Independent(LogNormal(self.loc, self.scale), 1)
        super().__init__(batch_shape=torch.Size(), event_shape=torch.Size([num_dim]))

    @property
    def mean(self):
        return torch.ones(self.num_dim, device=self.device)

    @property
    def variance(self):
        return torch.ones(self.num_dim, device=self.device)

    def sample(self, sample_shape=torch.Size()):
        if len(sample_shape) == 0:
            n_samples = 1
            squeeze = True
        else:
            n_samples = sample_shape[0]
            squeeze = False

        samples = self.base_dist.sample((n_samples,))
        mask = (samples >= self.low) & (samples <= self.high)
        valid_mask = mask.all(dim=1)
        
        while not valid_mask.all():
            num_resample = (~valid_mask).sum().item()
            resamples = self.base_dist.sample((num_resample,))
            samples[~valid_mask] = resamples
            mask = (samples >= self.low) & (samples <= self.high)
            valid_mask = mask.all(dim=1)

        if squeeze:
            return samples.squeeze(0)
        return samples

    def log_prob(self, value):
        log_prob = self.base_dist.log_prob(value)
        mask_invalid = ((value < self.low) | (value > self.high)).any(dim=-1)
        log_prob[mask_invalid] = float('-inf')
        return log_prob

def build_lognormal_multiplier_prior(low: list, high: list, device: torch.device):
    low_tensor = torch.tensor(low, dtype=torch.float32, device=device)
    high_tensor = torch.tensor(high, dtype=torch.float32, device=device)
    return TruncatedLogNormalPrior(len(low), low_tensor, high_tensor, device)

def main():
    device = torch.device('cpu')
    low = [0.2]*8
    high = [5.0]*8
    
    custom_prior = build_lognormal_multiplier_prior(low, high, device)
    
    # Process it for SBI
    prior, _, _ = process_prior(custom_prior)
    
    print("Prior created successfully.")
    print("Sample:", prior.sample((2,)))
    
    # Check if RestrictionEstimator works
    re = RestrictionEstimator(prior=prior)
    
    # Feed dummy data
    theta = prior.sample((100,))
    x = torch.randn(100, 288) # dummy CGM
    re.append_simulations(theta, x)
    
    re.train()
    restricted_prior = re.restrict_prior()
    
    print("Restricted Sample:", restricted_prior.sample((2,)))

if __name__ == '__main__':
    main()
