import torch
import torch.nn as nn
from transformers import CLIPModel, ViTModel

class CLIPBinaryClassifier(nn.Module):
    def __init__(self, model_name="openai/clip-vit-base-patch32", hidden_dim=128, model_type="clip"): # Removed use_original_image_size_feature
        super(CLIPBinaryClassifier, self).__init__()
        self.model_type = model_type.lower()

        if self.model_type == "clip":
            self.vision_backbone = CLIPModel.from_pretrained(model_name)
            # Freeze CLIP model parameters
            for param in self.vision_backbone.parameters():
                param.requires_grad = False
            # For CLIP, the vision part is accessed via vision_model
            vision_embedding_dim = self.vision_backbone.config.vision_config.hidden_size
        elif self.model_type == "vit":
            self.vision_backbone = ViTModel.from_pretrained(model_name)
            # Freeze ViT model parameters (optional, but consistent with CLIP freezing)
            for param in self.vision_backbone.parameters():
                param.requires_grad = False
            vision_embedding_dim = self.vision_backbone.config.hidden_size
        else:
            raise ValueError(f"Unsupported model_type: {model_type}. Choose 'clip' or 'vit'.")

        # Define the classifier head - always add 2 for original_image_size
        classification_head_input_dim = vision_embedding_dim + 2 
        
        self.hidden_dim = hidden_dim
        self.classifier = nn.Sequential(
            nn.Linear(classification_head_input_dim, hidden_dim),
            nn.LeakyReLU(0.2),
            nn.Linear(hidden_dim, 1) # 1 output for binary classification
        )

    def forward(self, pixel_values, original_image_size): # original_image_size is now required
        """
        Args:
            pixel_values: Tensor of preprocessed image data.
                          Expected shape: (batch_size, num_channels, height, width)
            original_image_size: Tensor of original image sizes (width, height), potentially normalized.
                                 Expected shape: (batch_size, 2). 
        """
        if self.model_type == "clip":
            # Get image features from the vision transformer part of CLIP
            vision_outputs = self.vision_backbone.vision_model(pixel_values=pixel_values)
            cls_embedding = vision_outputs.pooler_output # CLS token embedding
        elif self.model_type == "vit":
            # Get image features from ViTModel
            vision_outputs = self.vision_backbone(pixel_values=pixel_values)
            cls_embedding = vision_outputs.pooler_output # ViTModel also has pooler_output for CLS
        else: # Should not be reached if __init__ validation is correct
            raise ValueError(f"Unsupported model_type during forward pass: {self.model_type}")

        # Always use original_image_size
        if original_image_size is None: # Should not happen if called correctly
            raise ValueError("original_image_size must be provided.")
            
        # Ensure original_image_size is a float tensor and on the correct device
        original_image_size_f = original_image_size.float().to(cls_embedding.device)
        
        # Concatenate CLS embedding with original image size
        combined_features = torch.cat((cls_embedding, original_image_size_f), dim=1)
        
        # Pass combined features through the linear classifier
        logits = self.classifier(combined_features)
        return logits











if __name__ == '__main__':
    # Example usage (for testing the model structure)
    print("Testing CLIP model configuration:")
    try:
        # Example: Needs a dummy pixel_values and original_image_size to test forward pass
        clip_model_test = CLIPBinaryClassifier(model_name="openai/clip-vit-base-patch32", hidden_dim=64, model_type="clip")
        print("CLIPBinaryClassifier (type: clip) initialized.")
        print(f"  Classifier head: {clip_model_test.classifier}")
        # Dummy input for forward pass illustration (not run here)
        # dummy_pixels = torch.randn(2, 3, 224, 224)
        # dummy_sizes = torch.tensor([[224, 224], [300, 400]], dtype=torch.float) / 512.0 
        # logits = clip_model_test(dummy_pixels, dummy_sizes)
        # print(f"  Example logits shape: {logits.shape}")
    except Exception as e:
        print(f"Error initializing CLIP model: {e}")

    print("\\nTesting ViT model configuration:")
    try:
        vit_model_test = CLIPBinaryClassifier(model_name="google/vit-base-patch16-224-in21k", hidden_dim=64, model_type="vit")
        print("CLIPBinaryClassifier (type: vit) initialized.")
        print(f"  Classifier head: {vit_model_test.classifier}")
    except Exception as e:
        print(f"Error initializing ViT model: {e}")

    # To check trainable parameters (should only be the classifier's parameters if backbone is frozen)
    # print("\\nTrainable parameters (example for clip_model_test):")
    # if 'clip_model_test' in locals():
    #     for name, param in clip_model_test.named_parameters():
    #         if param.requires_grad:
    #             print(name)