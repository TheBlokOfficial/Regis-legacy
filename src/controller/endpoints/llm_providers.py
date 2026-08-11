from fastapi import APIRouter, HTTPException
from typing import List

from controller.config import loader as config
from controller.config.schemas import LlmProviderConfig, LlmProvidersConfig

router_llm_providers = APIRouter(prefix="/api/llm-providers", tags=["llm-providers"])



def _save_llm_providers(providers: list[LlmProviderConfig]) -> None:
    config.save(LlmProvidersConfig(providers))


def _get_llm_providers() -> list[LlmProviderConfig]:
    return config.load(LlmProvidersConfig).root


@router_llm_providers.get("", response_model=List[LlmProviderConfig])
def get_providers():
    providers = _get_llm_providers()
    masked = []
    for p in providers:
        p_copy = p.model_dump()
        if p_copy.get("api_key"):
            prefix = p_copy["api_key"][:3]
            p_copy["api_key"] = f"{prefix}...****"
        masked.append(LlmProviderConfig(**p_copy))
    return masked


@router_llm_providers.post("", response_model=LlmProviderConfig)
def add_provider(provider: LlmProviderConfig):
    providers = _get_llm_providers()
    if any(p.id == provider.id for p in providers):
        raise HTTPException(status_code=400, detail=f"Dostawca LLM z id '{provider.id}' już istnieje.")
    
    providers.append(provider)
    _save_llm_providers(providers)
    return provider


@router_llm_providers.patch("/{provider_id}", response_model=LlmProviderConfig)
def update_provider(provider_id: str, updates: dict):
    providers = _get_llm_providers()
    
    for idx, p in enumerate(providers):
        if p.id == provider_id:
            p_dict = p.model_dump()
            
            if "api_key" in updates and "..." in updates["api_key"]:
                del updates["api_key"]
                
            p_dict.update(updates)
            
            try:
                validated = LlmProviderConfig(**p_dict)
            except Exception as e:
                raise HTTPException(status_code=422, detail=str(e))
                
            providers[idx] = validated
            _save_llm_providers(providers)
            return validated
            
    raise HTTPException(status_code=404, detail="Dostawca LLM nie znaleziony")


@router_llm_providers.delete("/{provider_id}")
def delete_provider(provider_id: str):
    providers = _get_llm_providers()

    new_providers = [p for p in providers if p.id != provider_id]
    
    if len(new_providers) == len(providers):
        raise HTTPException(status_code=404, detail="Dostawca LLM nie znaleziony")
        
    _save_llm_providers(new_providers)
    return {"status": "ok"}
